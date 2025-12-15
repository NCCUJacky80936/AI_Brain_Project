# 檔案名稱: history_generator.py (v1.1 - MQTT 連線修正版)

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime, timedelta

# --- 設定區塊 ---
THINGSBOARD_HOST = 'localhost'
THINGSBOARD_PORT = 1883
ACCESS_TOKEN = 'myht969z6iqfkkpk31bf' # 使用您 MyTempSensor 設備的權杖

# --- 主要程式 ---

# ✨✨ 升級 ✨✨: 使用更穩健的 MQTT Client 初始化方式
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(ACCESS_TOKEN)

try:
    print(f"正在連線到 ThingsBoard -> {THINGSBOARD_HOST}:{THINGSBOARD_PORT}...")
    client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
    client.loop_start() 
    print("✅ 連線成功！準備開始生成歷史數據...")

    DAYS_TO_GENERATE = 5

    for i in range(1, DAYS_TO_GENERATE + 1):
        target_day = datetime.now() - timedelta(days=i)
        print(f"\n--- 正在生成 {target_day.strftime('%Y-%m-%d')} 的數據 ---")

        for _ in range(10):
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            random_second = random.randint(0, 59)
            timestamp_obj = target_day.replace(hour=random_hour, minute=random_minute, second=random_second)
            ts_ms = int(timestamp_obj.timestamp() * 1000)
            temperature_value = round(random.uniform(15.0, 25.0), 2)

            payload = {
                "ts": ts_ms,
                "values": {
                    "temperature": temperature_value
                }
            }
            
            payload_str = json.dumps(payload)
            client.publish('v1/devices/me/telemetry', payload_str)
            print(f"  已傳送 -> {payload_str}")
            time.sleep(0.1)

    print("\n✅ 所有歷史數據已生成完畢！")

except Exception as e:
    print(f"❌ 發生錯誤：{e}")

finally:
    time.sleep(1)
    client.loop_stop()
    client.disconnect()
    print("已斷開連線。")