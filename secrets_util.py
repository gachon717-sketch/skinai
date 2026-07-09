"""st.secrets 안전 접근 헬퍼.

.streamlit/secrets.toml 파일 자체가 없으면 st.secrets.get(key, default) 조차
StreamlitSecretNotFoundError 를 던지는 Streamlit의 동작 때문에, 로컬에서 secrets.toml을
아직 만들지 않은 상태로 실행하면 앱이 그대로 죽는다. 이를 방지하기 위한 안전한 wrapper.
"""
import streamlit as st


def get_secret(key: str, default: str = "") -> str:
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


def secrets_file_missing() -> bool:
    try:
        st.secrets.get("GEMINI_API_KEY", "")
        return False
    except Exception:
        return True
