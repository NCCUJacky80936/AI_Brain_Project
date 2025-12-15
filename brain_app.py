import requests
import json
import time
from flask import Flask, request, jsonify, render_template
from groq import Groq
from datetime import datetime, timedelta, date, time as dt_time
from itertools import groupby

# --- Part 1: 系統設定 ---
THINGSBOARD_URL = "http://localhost:9090"
THINGSBOARD_USERNAME = "tenant@thingsboard.org"
THINGSBOARD_PASSWORD = "tenant"
GROQ_API_KEY = "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"

# --- Part 2: 與 ThingsBoard 溝通的工具箱 ---
def get_thingsboard_token():
    login_url = f"{THINGSBOARD_URL}/api/auth/login"
    login_payload = {"username": THINGSBOARD_USERNAME, "password": THINGSBOARD_PASSWORD}
    try:
        response = requests.post(login_url, json=login_payload, timeout=10)
        response.raise_for_status()
        return response.json().get('token')
    except requests.exceptions.RequestException as e:
        return None

def get_all_devices(token):
    if not token: return None
    headers = {"Content-Type": "application/json", "X-Authorization": f"Bearer {token}"}
    devices_url = f"{THINGSBOARD_URL}/api/tenant/devices?pageSize=100&page=0"
    try:
        response = requests.get(devices_url, headers=headers)
        response.raise_for_status()
        devices = [{"name": d.get("name"), "id": d.get("id", {}).get("id")} for d in response.json().get("data", [])]
        return devices
    except Exception as e:
        return []

def get_historical_telemetry(token, device_id, keys, start_ts, end_ts, agg='NONE', interval='3600000'):
    headers = {"Content-Type": "application/json", "X-Authorization": f"Bearer {token}"}
    url_params = f"keys={keys}&startTs={start_ts}&endTs={end_ts}&agg={agg}"
    if agg == 'NONE':
        url_params += "&limit=10000"
    else:
        url_params += f"&interval={interval}"
    
    telemetry_url = f"{THINGSBOARD_URL}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?{url_params}"
    
    try:
        response = requests.get(telemetry_url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ 獲取歷史數據失敗 (device: {device_id}, keys: {keys}): {e}")
        return {}
        
def create_new_device(token, device_name):
    if not token or not device_name: return None
    headers = {"Content-Type": "application/json", "X-Authorization": f"Bearer {token}"}
    device_url = f"{THINGSBOARD_URL}/api/device"
    payload = {"name": device_name}
    try:
        response = requests.post(device_url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

# --- Part 3: 我們的大腦主程式 (Flask Web App) ---
app = Flask(__name__)
try:
    groq_client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    groq_client = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/devices", methods=['GET'])
def api_get_devices():
    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500
    devices = get_all_devices(token)
    return jsonify(devices)

@app.route("/api/device/<device_id>/latest", methods=['GET'])
def api_get_latest(device_id):
    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500
    end_ts = int(time.time() * 1000)
    start_ts = int((time.time() - timedelta(hours=12).total_seconds()) * 1000)
    latest_data = get_historical_telemetry(token, device_id, 'temperature', start_ts, end_ts)
    return jsonify(latest_data)

@app.route("/api/device/<device_id>/history", methods=['GET'])
def api_get_history(device_id):
    key = request.args.get('key', 'temperature')
    days = int(request.args.get('days', 7))
    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500
    now = datetime.now()
    today_start = datetime.combine(now.date(), dt_time.min)
    end_ts = int(now.timestamp() * 1000)
    start_ts = int((today_start - timedelta(days=days-1)).timestamp() * 1000)
    history_data = get_historical_telemetry(token, device_id, key, start_ts, end_ts, agg='AVG', interval='86400000')
    return jsonify(history_data)

@app.route("/api/device", methods=['POST'])
def api_create_device():
    data = request.json
    device_name = data.get('name')
    if not device_name: return jsonify({"error": "需要設備名稱"}), 400
    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500
    new_device = create_new_device(token, device_name)
    if new_device: return jsonify(new_device)
    else: return jsonify({"error": "建立設備失敗"}), 500

@app.route("/api/device/<device_id>/stats", methods=['GET'])
def api_get_stats(device_id):
    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500

    now = datetime.now()
    today_start = datetime.combine(now.date(), dt_time.min)
    
    today_start_ts = int(today_start.timestamp() * 1000)
    week_start_ts = int((today_start - timedelta(days=6)).timestamp() * 1000)
    month_start_ts = int((today_start - timedelta(days=29)).timestamp() * 1000)
    end_ts = int(now.timestamp() * 1000)

    weekly_raw_data = get_historical_telemetry(token, device_id, 'temperature', week_start_ts, end_ts)
    if not weekly_raw_data or 'temperature' not in weekly_raw_data or not weekly_raw_data['temperature']:
        return jsonify({"error": "過去7天內沒有找到溫度數據"}), 404
    
    temp_values_full_week = [float(item['value']) for item in weekly_raw_data['temperature'] if item['value'] is not None]
    if not temp_values_full_week: return jsonify({"error": "過去7天內的溫度數據皆為空值"}), 404
    
    stats = {}
    today_values = [float(item['value']) for item in weekly_raw_data['temperature'] if item['ts'] >= today_start_ts and item['value'] is not None]
    if today_values:
        stats['today'] = {'max': round(max(today_values), 2), 'min': round(min(today_values), 2), 'avg': round(sum(today_values) / len(today_values), 2)}

    stats['week'] = {'max': round(max(temp_values_full_week), 2), 'min': round(min(temp_values_full_week), 2), 'avg': round(sum(temp_values_full_week) / len(temp_values_full_week), 2), 'diff': round(max(temp_values_full_week) - min(temp_values_full_week), 2)}

    daily_stats = []
    sorted_weekly_data = sorted(weekly_raw_data['temperature'], key=lambda x: x['ts'])
    grouped_by_day = groupby(sorted_weekly_data, key=lambda x: date.fromtimestamp(x['ts']/1000).isoformat())
    for day_str, group in grouped_by_day:
        day_values = [float(item['value']) for item in group if item['value'] is not None]
        if day_values:
            daily_stats.append({'date': day_str, 'max': round(max(day_values), 2), 'min': round(min(day_values), 2), 'avg': round(sum(day_values) / len(day_values), 2), 'diff': round(max(day_values) - min(day_values), 2)})
    stats['daily_breakdown'] = sorted(daily_stats, key=lambda x: x['date'], reverse=True)

    month_agg_data = get_historical_telemetry(token, device_id, 'temperature', month_start_ts, end_ts, agg='AVG', interval='86400000')
    if month_agg_data and 'temperature' in month_agg_data:
        month_values = [float(item['value']) for item in month_agg_data['temperature'] if item['value'] is not None]
        if month_values:
            stats['month_avg'] = round(sum(month_values) / len(month_values), 2)

    return jsonify(stats)

# --- ✨✨ 這裡是我們唯一的、最重要的升級 ✨✨ ---
@app.route("/ask", methods=['GET'])
def ask_brain():
    user_question = request.args.get('q', '這台設備現在狀況如何？')
    device_id = request.args.get('deviceId', None)
    if not device_id: return jsonify({"error": "請提供 deviceId"}), 400
    if not groq_client: return jsonify({"error": "GROQ AI 未初始化"}), 500

    token = get_thingsboard_token()
    if not token: return jsonify({"error": "無法登入ThingsBoard"}), 500
    
    keys_for_ai = 'temperature' # 我們只專注於分析溫度
    end_ts = int(time.time() * 1000)
    start_ts = int((time.time() - timedelta(days=30).total_seconds()) * 1000)
    sensor_data = get_historical_telemetry(token, device_id, keys_for_ai, start_ts, end_ts, agg='NONE')

    if not sensor_data or 'temperature' not in sensor_data or not sensor_data['temperature']:
        return jsonify({"error": f"無法從 ThingsBoard 取得設備 {device_id} 的歷史數據。"}), 500

    # --- ✨✨ 全新 ✨✨: Python 數據摘要核心 ---
    # 在將數據發送給 AI 之前，先進行預處理和摘要
    daily_summary = []
    sorted_data = sorted(sensor_data['temperature'], key=lambda x: x['ts'])
    grouped_by_day = groupby(sorted_data, key=lambda x: date.fromtimestamp(x['ts']/1000).isoformat())
    
    for day_str, group in grouped_by_day:
        day_values = [float(item['value']) for item in group if item['value'] is not None]
        if day_values:
            daily_summary.append({
                'date': day_str,
                'avg_temp': round(sum(day_values) / len(day_values), 2),
                'max_temp': round(max(day_values), 2),
                'min_temp': round(min(day_values), 2),
                'readings_count': len(day_values)
            })
    # ----------------------------------------------
    
    prompt_for_ai = f"""
    請扮演一位頂尖的 AIoT 數據分析師。
    
    背景資料：我已經為你將指定設備在「過去 30 天」內的詳細感測器數據，預先處理並整理成了一份簡潔的「每日數據摘要報告」：
    ---
    {json.dumps(daily_summary, indent=2, ensure_ascii=False)}
    ---

    你的任務是：根據上面這份**摘要報告**，精準地、只針對使用者提出的「具體問題」進行深入的分析和回答。
    
    例如：
    - 如果使用者問「昨天」的狀況，你就專注分析摘要中昨天的數據。
    - 如果使用者問「這週」的趨勢，你就分析摘要中最近七天的數據變化。

    請用親切、專業、且口語化的繁體中文來回答。
    
    使用者的具體問題如下：
    問題："{user_question}"

    ---
    **最終指令：** 你的回答必須完全基於上面提供的「每日數據摘要報告」，並且只能使用**繁體中文**。
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt_for_ai}],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        ai_answer = chat_completion.choices[0].message.content
        return jsonify({"ai_analysis": ai_answer})
    except Exception as e:
        return jsonify({"error": f"呼叫 GROQ AI 時發生錯誤: {e}"}), 500

# --- Part 4: 啟動我們的服務 ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)