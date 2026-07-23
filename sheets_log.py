"""구글 스프레드시트에 익명 분석 데이터를 축적하는 모듈.

secrets에 [gcp_service_account] 섹션과 GSHEET_ID가 설정된 경우에만 동작하며,
설정이 없거나 오류가 나도 앱 동작에는 절대 영향을 주지 않는다 (조용히 스킵).

기록 내용은 전부 익명: 이름·연락처·사진은 저장하지 않는다.
- 'analyses' 시트: 분석 1건당 1행 (시각, 모드, 유입경로, 성별, 연령대, 바우만, 점수 7종, 고민, 특징, 추천시술)
- 'clicks' 시트: 리뷰/카톡 버튼 클릭 1건당 1행 (시각, 종류, 유입경로)
"""
import datetime
import threading

import streamlit as st

from secrets_util import get_secret

ANALYSIS_HEADERS = [
    "시각", "모드", "유입경로", "성별", "연령대", "바우만타입",
    "피부톤균일도", "주름개선도", "모공관리도", "피부결매끄러움", "유수분밸런스", "홍조안정도", "색소침착도",
    "주요고민", "피부특징", "추천시술", "추천부스터",
]
CLICK_HEADERS = ["시각", "종류", "유입경로"]


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def enabled() -> bool:
    try:
        return bool(get_secret("GSHEET_ID")) and "gcp_service_account" in st.secrets
    except Exception:
        return False


def _open_sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(get_secret("GSHEET_ID"))


def _append(worksheet_name: str, headers: list, row: list):
    try:
        sh = _open_sheet()
        try:
            ws = sh.worksheet(worksheet_name)
        except Exception:
            ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=len(headers))
            ws.append_row(headers)
        ws.append_row(row)
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
    score_cols = [
        scores.get(k, "") for k in
        ["피부톤균일도", "주름개선도", "모공관리도", "피부결매끄러움", "유수분밸런스", "홍조안정도", "색소침착도"]
    ]
    lesions = " / ".join(l.get("name", "") for l in result.get("detected_lesions", []))
    treatments = " / ".join(t.get("name", "") for t in result.get("recommended_treatments", []))
    boosters = " / ".join(b.get("name", "") for b in result.get("recommended_boosters", []))
    row = [
        _now(), mode, src or "직접접속", gender or "미입력", _age_band(age), baumann_code or "",
        *score_cols,
        (notes or "")[:100], lesions, treatments, boosters,
    ]
    threading.Thread(target=_append, args=("analyses", ANALYSIS_HEADERS, row), daemon=True).start()


def log_click(click_type: str, src: str):
    """리뷰/카톡 버튼 클릭 기록. click_type: 'review' | 'kakao'"""
    if not enabled():
        return
    row = [_now(), click_type, src or "직접접속"]
    threading.Thread(target=_append, args=("clicks", CLICK_HEADERS, row), daemon=True).start()
