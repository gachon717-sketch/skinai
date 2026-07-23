"""사용 통계 (분석 횟수 / 리뷰 버튼 클릭 수) — 관리자 전용.

로컬 JSON 파일에 저장한다. Streamlit Cloud에서는 재배포/재시작 시 파일이 초기화되므로
장기 운영 시 Google Sheets 등 외부 저장소로 업그레이드 필요.
"""
import datetime
import json
import os
import threading

STATS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "usage_stats.json")
_lock = threading.Lock()

_EMPTY = {"analyses": 0, "review_clicks": 0, "daily": {}}


def _load() -> dict:
    try:
        with open(STATS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(_EMPTY)


def increment(key: str, src: str = ""):
    """key: 'analyses' | 'review_clicks' | 'kakao_clicks'. src: 유입경로(youtube/insta 등)"""
    with _lock:
        data = _load()
        data[key] = data.get(key, 0) + 1
        today = datetime.date.today().isoformat()
        day = data.setdefault("daily", {}).setdefault(today, {})
        day[key] = day.get(key, 0) + 1
        if src:
            by_src = data.setdefault("by_src", {}).setdefault(src, {})
            by_src[key] = by_src.get(key, 0) + 1
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        except Exception:
            pass  # 통계 기록 실패가 앱 동작을 막으면 안 됨


def analyses_today() -> int:
    data = _load()
    today = datetime.date.today().isoformat()
    return data.get("daily", {}).get(today, {}).get("analyses", 0)


def get_stats() -> dict:
    return _load()


def today_stats() -> dict:
    data = _load()
    today = datetime.date.today().isoformat()
    return data.get("daily", {}).get(today, {})
