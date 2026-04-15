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

# main.py と同じディレクトリの index.html / app.js / style.css を配信する
BASE_DIR = Path(__file__).resolve().parent

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 区間設定（追加・変更・URL差し替えはここだけ触ればOK）
# ==========================================
# 各要素:
#   from_stop / to     : 画面・APIフィルタ用の停留所名（伊丹市バスサイトの表記と一致させる）
#   heading            : 「○○行き」の○○部分（例: 塚口、南菱、野間口）
#   filter_to          : APIの bus["to"] との照合用（この区間で次に来る便を選ぶ）
#   base_url           : willDepartureTime3 等を返す JSON の取得元（末尾の &_= は付けない）
#   default_route      : データなし時に返す路線表示用（例: 「未定」）
#
# ---------------------------------------------------------------------------
# 【重要】以下 PLACEHOLDER の URL はダミーです。
# 実際の伊丹市バス JSON の URL/クエリが分かり次第、該当する base_url を差し替えてください。
# ---------------------------------------------------------------------------

BUS_SEGMENTS: list[dict[str, Any]] = [
    {
        "id": "nomaguchi_tsukaguchi_41",
        "from_stop": "野間口",
        "to": "塚口",
        "heading": "塚口",
        "filter_to": "塚口",
        "default_route": "未定",
        # 既存: 野間口 → 塚口（実データ）
        "base_url": (
            "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?"
            "tabName=&selectedLandmarkCatCd=&"
            "from=%E9%87%8E%E9%96%93%E5%8F%A3&fromType=&"
            "to=%E5%A1%9A%E5%8F%A3&toType=1&locale=ja&fromlat=&fromlng=&"
            "tolat=34.763623&tolng=135.40084&sortBy=1&routeLayoutCd=&"
            "fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&"
            "autoRefresh=30&fromDisplayOrder=&toDisplayOrder="
        ),
    },
    {
        "id": "nomahigashi_tsukaguchi",
        "from_stop": "野間東",
        "to": "塚口",
        "heading": "塚口",
        "filter_to": "塚口",
        "default_route": "未定",
        # TODO: 【ここに野間東のURLを設定してください】伊丹市バス JSON 取得用の正しい base_url に差し替え
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E9%87%8E%E9%96%93%E6%9D%B1&fromType=1&to=%E5%A1%9A%E5%8F%A3&toType=&locale=ja&fromlat=34.753847&fromlng=135.414502&tolat=&tolng=&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder=&_=1776146131481",
    },
    {
        "id": "tsukaguchi_nanryo",
        "from_stop": "塚口",
        "to": "南菱",
        "heading": "南菱",
        "filter_to": "南菱",
        "default_route": "未定",
        "base_url": (
            "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?"
            "tabName=&selectedLandmarkCatCd=&"
            "from=%E5%A1%9A%E5%8F%A3&fromType=1&"
            "to=%E5%8D%97%E8%8F%B1&toType=1&locale=ja&"
            "fromlat=34.753847&fromlng=135.414502&"
            "tolat=34.770085&tolng=135.405702&"
            "sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&"
            "existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder="
        ),
    },
    {
        "id": "tsukaguchi_nomaguchi",
        "from_stop": "塚口",
        "to": "野間口",
        "heading": "野間口",
        "filter_to": "野間口",
        "default_route": "未定",
        # TODO: 【塚口発・野間口行のURLを設定してください】
        "base_url": "https://itamicity-bus.bus-navigation.jp/wgsys/wgss/busMarkImg.htm?tabName=&selectedLandmarkCatCd=&from=%E5%A1%9A%E5%8F%A3&fromType=1&to=%E9%87%8E%E9%96%93%E5%8F%A3&toType=1&locale=ja&fromlat=34.753847&fromlng=135.414502&tolat=34.766461&tolng=135.398368&sortBy=1&routeLayoutCd=&fromSignpoleKey=&bsid=4&mapFlag=true&existYn=N&routeKey=&autoRefresh=30&fromDisplayOrder=&toDisplayOrder=&_=1776146476553",
    },
]


def _normalize_eta(bus: dict) -> Optional[int]:
    raw = bus.get("willDepartureTime3")
    if raw is None or raw == "":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _fetch_segment_buses(segment: dict[str, Any]) -> dict[str, Any]:
    """
    1区間について次に来る1便（eta 最小）を返す。
    取得失敗・該当なしの場合は eta は null、route は default_route を使う。
    """
    out = {
        "from_stop": segment["from_stop"],
        "to": segment["to"],
        "heading": segment["heading"],
        "route": segment.get("default_route", "未定"),
        "eta": None,
        "delay": 0,
    }

    base = segment.get("base_url") or ""
    if not base.strip() or "example.com/placeholder" in base:
        return out

    try:
        current_timestamp = int(time.time() * 1000)
        request_url = f"{base}&_={current_timestamp}"
        response = requests.get(request_url, timeout=5)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"区間 {segment.get('id')}: データ取得エラー: {e}")
        return out

    filter_to = segment.get("filter_to")
    candidates: list[dict] = []

    for bus in data.get("busData", []) or []:
        if filter_to is not None and bus.get("to") != filter_to:
            continue
        eta = _normalize_eta(bus)
        if eta is None:
            continue
        delay_raw = bus.get("delayTime")
        try:
            delay = int(delay_raw) if delay_raw not in (None, "") else 0
        except (TypeError, ValueError):
            delay = 0
        candidates.append(
            {
                "route": bus.get("rollsignName") or segment.get("default_route", "未定"),
                "eta": eta,
                "delay": delay,
            }
        )

    if not candidates:
        return out

    candidates.sort(key=lambda x: x["eta"])
    best = candidates[0]
    out["route"] = best["route"]
    out["eta"] = best["eta"]
    out["delay"] = best["delay"]
    return out


@app.get("/bus")
def get_bus():
    """
    全区間の次便を配列で返す（設定 BUS_SEGMENTS と同じ順序）。
    例:
    [
      {"from_stop": "野間口", "to": "塚口", "heading": "塚口", "route": "41", "eta": 5, "delay": 0},
      ...
    ]
    """
    with ThreadPoolExecutor(max_workers=min(8, len(BUS_SEGMENTS) or 1)) as pool:
        futures = [pool.submit(_fetch_segment_buses, seg) for seg in BUS_SEGMENTS]
        results = []
        for f in futures:
            results.append(f.result())
    # レスポンスは heading を含む（フロントで「○○行き」を組み立てる）
    slim = []
    for r in results:
        item = {
            "from_stop": r["from_stop"],
            "to": r["to"],
            "route": r["route"],
            "eta": r["eta"],
            "delay": r["delay"],
        }
        if "heading" in r:
            item["heading"] = r["heading"]
        slim.append(item)
    return slim


@app.get("/")
def read_index():
    """ルートで index.html を返す（http://127.0.0.1:8000/ で画面表示）"""
    return FileResponse(BASE_DIR / "index.html")


@app.get("/manifest.json")
def read_manifest():
    """PWA 用 Web App Manifest（ホーム画面追加・アドレスバー色など）"""
    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
def read_service_worker():
    """
    Service Worker をサイト直下で配信（scope '/' で登録可能にする）。
    /static/sw.js だとスコープが /static に限定されるためルート用ルートを用意。
    """
    return FileResponse(
        BASE_DIR / "sw.js",
        media_type="application/javascript",
    )


# フォルダ内のファイルを "/static" という名前ではなく、直接読み込めるようにします
app.mount("/", StaticFiles(directory=str(BASE_DIR), html=True), name="static")
