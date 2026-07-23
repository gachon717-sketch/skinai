"""구글 스프레드시트에 익명 분석 데이터를 축적하는 모듈 (Apps Script 웹훅 방식).

서비스 계정 키 대신, 구글 시트에 붙인 Apps Script 웹앱으로 HTTP POST를 보낸다.
- 서비스 계정/JSON 키 불필요 (조직 보안정책과 무관)
- 표준 라이브러리(urllib)만 사용 → 추가 의존성 없음
- secrets에 GSHEET_WEBHOOK_URL 이 있을 때만 동작, 없거나 실패해도 앱 동작엔 영향 없음

기록 내용은 전부 익명: 이름·연락처·사진은 저장하지 않는다.
"""
import datetime
import json
import threading
import urllib.request

from secrets_util import get_secret


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def enabled() -> bool:
    return bool(get_secret("GSHEET_WEBHOOK_URL"))


def _post(payload: dict):
    url = get_secret("GSHEET_WEBHOOK_URL")
    if not url:
        return
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass  # 기록 실패는 조용히 무시 — 고객 화면에 영향 금지


def _age_band(age: int) -> str:
    if not age or age <= 0:
        return ""
    return f"{(age // 10) * 10}대"


def log_analysis(mode: str, src: str, gender: str, age: int, baumann_code: str,
                 scores: dict, notes: str, result: dict):
    """분석 완료 1건 기록 (백그라운드 스레드 — UI 지연 없음)"""
    if not enabled():
        return
    lesions = " / ".join(l.get("name", "") for l in result.get("detected_lesions", []))
    treatments = " / ".join(t.get("name", "") for t in result.get("recommended_treatments", []))
    boosters = " / ".join(b.get("name", "") for b in result.get("recommended_boosters", []))
    payload = {
        "sheet": "analyses",
        "row": [
            _now(), mode, src or "직접접속", gender or "미입력", _age_band(age), baumann_code or "",
            scores.get("피부톤균일도", ""), scores.get("주름개선도", ""), scores.get("모공관리도", ""),
            scores.get("피부결매끄러움", ""), scores.get("유수분밸런스", ""), scores.get("홍조안정도", ""),
            scores.get("색소침착도", ""),
            (notes or "")[:100], lesions, treatments, boosters,
        ],
    }
    threading.Thread(target=_post, args=(payload,), daemon=True).start()


def log_click(click_type: str, src: str):
    """리뷰/카톡 버튼 클릭 기록. click_type: 'review' | 'kakao'"""
    if not enabled():
        return
    payload = {"sheet": "clicks", "row": [_now(), click_type, src or "직접접속"]}
    threading.Thread(target=_post, args=(payload,), daemon=True).start()
