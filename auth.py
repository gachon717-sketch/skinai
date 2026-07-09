"""2주(14일) 주기로 자동 갱신되는 접속 비밀번호 로직.

비밀번호는 재배포 없이 시간에 따라 자동으로 바뀐다 (secrets의 PASSWORD_SECRET + 14일 주기 인덱스로 결정).
병원 직원은 사이드바의 관리자 패널(ADMIN_KEY)에서 현재/다음 비밀번호를 확인해 환자에게 안내한다.
"""
import datetime
import hashlib
import hmac
from typing import Optional

ROTATE_DAYS = 14
EPOCH = datetime.date(2026, 1, 1)  # 주기 계산 기준일 (임의로 고정, 변경 금지)


def _period_index(today: Optional[datetime.date] = None) -> int:
    today = today or datetime.date.today()
    delta_days = (today - EPOCH).days
    return delta_days // ROTATE_DAYS


def _period_bounds(period: int) -> tuple[datetime.date, datetime.date]:
    start = EPOCH + datetime.timedelta(days=period * ROTATE_DAYS)
    end = start + datetime.timedelta(days=ROTATE_DAYS) - datetime.timedelta(days=1)
    return start, end


def _generate_password(period: int, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), f"skinai-v1-{period}".encode("utf-8"), hashlib.sha256).hexdigest()
    num = int(digest, 16) % 1_000_000
    return f"{num:06d}"


def current_password(secret: str) -> str:
    return _generate_password(_period_index(), secret)


def current_period_info(secret: str) -> dict:
    idx = _period_index()
    start, end = _period_bounds(idx)
    return {
        "password": _generate_password(idx, secret),
        "start": start,
        "end": end,
        "next_password": _generate_password(idx + 1, secret),
        "next_start": end + datetime.timedelta(days=1),
    }


def check_password(entered: str, secret: str) -> bool:
    if not secret:
        return False
    return entered.strip() == current_password(secret)
