import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# ディレクトリ設定
BASE_DIR = Path(__file__).resolve().parent

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# バス停設定（既存のものを維持）
BUS_SEGMENTS: list[dict[str, Any]] = [
    {
        "id": "nomaguchi_tsukaguchi_41",
        "from_stop": "野間口",
        "to": "塚口",
        "heading": "塚口",
        "filter_to": "塚口",
        "default_route": "41",
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E9%87%8E%E9%96%93%E5%8F%A3&fromType=&to=%E5%A1%9A%E5%8F%A3&toType=1&locale=ja&fromlat=&fromlng=&tolat=34.763623&tolng=135.40084&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder="
    },
    {
        "id": "nomahigashi_tsukaguchi",
        "from_stop": "野間東",
        "to": "塚口",
        "heading": "塚口",
        "filter_to": "塚口",
        "default_route": "未定",
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E9%87%8E%E9%96%93%E6%9D%B1&fromType=1&to=%E5%A1%9A%E5%8F%A3&toType=&locale=ja&fromlat=34.753847&fromlng=135.414502&tolat=&tolng=&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder=&_=1776146131481"
    },
    {
        "id": "tsukaguchi_nanryo",
        "from_stop": "塚口",
        "to": "南菱",
        "heading": "南菱",
        "filter_to": "南菱",
        "default_route": "未定",
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E5%A1%9A%E5%8F%A3&fromType=1&to=%E5%8D%97%E8%8F%B1&toType=1&locale=ja&fromlat=34.753847&fromlng=135.414502&tolat=34.770085&tolng=135.405702&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder="
    },
    {
        "id": "tsukaguchi_nomaguchi",
        "from_stop": "塚口",
        "to": "野間口",
        "heading": "野間口",
        "filter_to": "野間口",
        "default_route": "未定",
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E5%A1%9A%E5%8F%A3&fromType=1&to=%E9%87%8E%E9%96%93%E5%8F%A3&toType=1&locale=ja&fromlat=34.753847&fromlng=135.414502&tolat=34.766461&tolng=135.398368&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder=&_=1776146476553"
    }
]

def _normalize_eta(bus: dict) -> Optional[int]:
    raw = bus.get("willDepartureTime3")
    if not raw: return None
    try: return int(raw)
    except: return None

def _fetch_segment_buses(segment: dict[str, Any]) -> dict[str, Any]:
    out = {"from_stop": segment["from_stop"], "to": segment["to"], "heading": segment["heading"], "route": segment.get("default_route", "未定"), "eta": None, "delay": 0}
    try:
        url = f"{segment['base_url']}&_={int(time.time() * 1000)}"
        res = requests.get(url, timeout=5)
        data = res.json()
        candidates = []
        for bus in data.get("busData", []):
            if segment.get("filter_to") and bus.get("to") != segment["filter_to"]: continue
            eta = _normalize_eta(bus)
            if eta is None: continue
            candidates.append({"route": bus.get("rollsignName") or segment["default_route"], "eta": eta, "delay": int(bus.get("delayTime") or 0)})
        if candidates:
            candidates.sort(key=lambda x: x["eta"])
            best = candidates[0]
            out.update(best)
    except Exception as e:
        print(f"Error fetching {segment['id']}: {e}")
    return out

@app.get("/bus")
def get_bus():
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(_fetch_segment_buses, BUS_SEGMENTS))
    return results

# --- main.py の一番最後をこのように修正 ---

# --- main.py の一番最後をこの 7行 に差し替え ---

@app.get("/")
def read_index():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/{file_path:path}")
def read_static(file_path: str):
    # 1. まずそのまま探す
    file_full_path = BASE_DIR / file_path
    if file_full_path.is_file():
        return FileResponse(file_full_path)
    
    # 2. もし見つからなければ、ファイル名の先頭を大文字にして探す (app.js -> App.js)
    alt_path = BASE_DIR / file_path.capitalize()
    if alt_path.is_file():
        return FileResponse(alt_path)
    
    # 3. それでもダメなら小文字にして探す (App.js -> app.js)
    alt_path_low = BASE_DIR / file_path.lower()
    if alt_path_low.is_file():
        return FileResponse(alt_path_low)

    return {"detail": f"File {file_path} not found"}