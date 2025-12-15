# 檔案名稱: sensor_simulator.py (v2.1 - 穩定連線修正版)
# ---------------------------------------------------------------------------
import paho.mqtt.client as mqtt
import json
import time
import random

# --- 設定區塊 ---
THINGSBOARD_HOST = 'localhost'
THINGSBOARD_PORT = 1883
ACCESS_TOKEN = 'myht969z6iqfkkpk31bf' # 這裡使用您 MyTempSensor 設備的權杖

# --- MQTT 連線與發布 ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="temp_sensor_simulator_stable")
client.username_pw_set(ACCESS_TOKEN)

try:
    print(f"正在連線到 ThingsBoard -> {THINGSBOARD_HOST}:{THINGSBOARD_PORT}...")
    client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
    print("✅ 連線成功！準備開始傳送數據...")

    # ✨✨ 升級 ✨✨: 啟用一個「背景執行緒」，專門負責處理網路通訊和「報平安」
    client.loop_start() 

    while True:
        # 主執行緒的邏輯完全不變，專心產生和發送數據
        temperature_value = round(random.uniform(25.0, 30.0), 2)
        payload = {'temperature': temperature_value}
        payload_str = json.dumps(payload)
        client.publish('v1/devices/me/telemetry', payload_str)
        print(f"已傳送數據 -> {payload_str}")

        # 我們仍然等待 200 秒，但這次的 sleep 不會再影響到背景的「報平安」工作了
        time.sleep(200)

except KeyboardInterrupt:
    # ✨✨ 優化 ✨✨: 讓我們可以優雅地用 Ctrl+C 停止程式
    print("\n程式已手動停止。")
except Exception as e:
    print(f"❌ 發生錯誤：{e}")

finally:
    # ✨✨ 升級 ✨✨: 停止背景執行緒
    client.loop_stop()
    client.disconnect()
    print("已斷開連線。")