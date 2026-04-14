import time
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🎯 設定エリア
# ==========================================
TARGET_TO = "塚口" 

# 👇 最後の `&_=` の部分を削ったベースURLを用意します
BASE_API_URL = "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E9%87%8E%E9%96%93%E5%8F%A3&fromType=&to=%E5%A1%9A%E5%8F%A3&toType=1&locale=ja&fromlat=&fromlng=&tolat=34.763623&tolng=135.40084&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder="
# ==========================================

@app.get("/bus")
def get_bus():
    try:
        # --------------------------------------------------
        # 【キャッシュ対策】現在時刻（ミリ秒）を取得してURLに付与する 
        # --------------------------------------------------
        current_timestamp = int(time.time() * 1000)
        request_url = f"{BASE_API_URL}&_={current_timestamp}"

        # 実データを取得
        response = requests.get(request_url, timeout=5)
        response.raise_for_status()
        data = response.json() 

        result = []

        for bus in data.get("busData", []):
            
            if bus.get("to") != TARGET_TO:
                continue 

            eta_str = bus.get("willDepartureTime3")
            if not eta_str:
                continue

            eta = int(eta_str)
            delay = int(bus["delayTime"]) if bus.get("delayTime") else 0

            result.append({
                "route": bus["rollsignName"],
                "to": bus["to"],
                "eta": eta,
                "delay": delay
            })

        # 到着が近い順にソート
        result.sort(key=lambda x: x["eta"])

        # 最も近い1件のみを返す
        return result[:1]

    except Exception as e:
        print(f"データ取得エラー: {e}")
        return []