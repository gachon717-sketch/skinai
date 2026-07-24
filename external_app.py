"""SNS 공개용 앱 진입점 (external 모드).

Streamlit Cloud는 "저장소 + 브랜치 + 메인파일" 조합으로 앱을 구분하므로,
병원용(streamlit_app.py)과 별개의 앱으로 배포하려면 진입 파일이 달라야 한다.
이 파일을 Main file path 로 지정해 배포하면 자동으로 external 모드로 켜진다.
(secrets에 MODE를 넣지 않아도 됨 — 여기서 강제 지정)

병원용 앱은 기존처럼 streamlit_app.py 를 그대로 사용하며 아무 영향도 받지 않는다.
"""
import os

os.environ["SKINAI_MODE"] = "external"  # streamlit_app import 전에 지정해야 함

import streamlit_app  # noqa: E402  (모듈 로드 시 페이지 설정·CSS 적용)

streamlit_app.main()
