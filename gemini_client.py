"""Gemini API 호출 래퍼 (google-genai SDK).

두 가지 인증 방식을 지원한다:
1. Vertex AI 모드 — secrets에 VERTEX_PROJECT(프로젝트 ID)가 있으면 사용.
   기존 내부용 앱(server.py)과 동일하게 gcloud 로그인(ADC) 인증으로 Google Cloud
   크레딧을 사용한다. 병원 PC처럼 `gcloud auth application-default login`이
   완료된 컴퓨터에서 동작.
2. API 키 모드 — GEMINI_API_KEY("AIza..." 형식)가 있으면 사용.
   Streamlit Cloud 등 gcloud 인증이 없는 환경용.
둘 다 설정된 경우 Vertex AI 모드를 우선한다.
"""
import io
import json

from PIL import Image
from google import genai
from google.genai import types

from secrets_util import get_secret

DIR_LABEL = {"front": "정면", "left": "좌측 측면", "right": "우측 측면"}


def prepare_image_bytes(uploaded_file, max_side: int = 1440, quality: int = 85) -> bytes:
    """업로드/촬영된 이미지를 리사이즈 + JPEG 압축하여 전송 용량을 줄인다."""
    img = Image.open(uploaded_file)
    img = img.convert("RGB")
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1:
        img = img.resize((int(w * scale), int(h * scale)))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _get_client() -> genai.Client:
    project = get_secret("VERTEX_PROJECT")
    if project:
        location = get_secret("VERTEX_LOCATION", "us-central1")
        return genai.Client(vertexai=True, project=project, location=location)

    api_key = get_secret("GEMINI_API_KEY")
    if api_key and api_key.startswith("AIza"):
        return genai.Client(api_key=api_key)

    raise RuntimeError(
        "AI 인증이 설정되지 않았습니다. .streamlit/secrets.toml 에 "
        "VERTEX_PROJECT(Google Cloud 프로젝트 ID, gcloud 로그인 필요) 또는 "
        "GEMINI_API_KEY(https://aistudio.google.com/apikey 발급, AIza로 시작) "
        "중 하나를 설정하고 앱을 다시 시작하세요."
    )


def _parse_json_loose(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 응답이 잘린 경우 마지막 완전한 '}' 지점까지 자르고 괄호를 맞춰 복구 시도
        last = text.rfind("}")
        if last <= 0:
            raise
        fixed = text[: last + 1]
        opens, closes = fixed.count("{"), fixed.count("}")
        fixed += "}" * max(0, opens - closes)
        return json.loads(fixed)


def make_client() -> genai.Client:
    """메인 스레드에서 미리 클라이언트를 만들 때 사용 (secrets 접근은 메인 스레드에서만)."""
    return _get_client()


def analyze_skin(photos: dict, system_prompt: str, model_name: str = "gemini-2.5-pro", client: genai.Client = None) -> dict:
    """photos: {"front"/"left"/"right": jpeg bytes}"""
    if client is None:
        client = _get_client()

    contents = []
    for key, img_bytes in photos.items():
        if not img_bytes:
            continue
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
        contents.append(f"[{DIR_LABEL.get(key, key)} 사진]")

    if not contents:
        raise ValueError("분석할 사진이 없습니다.")

    contents.append("위 스마트폰 촬영 사진을 종합 분석하여 JSON 형식으로만 응답해주세요. (마크다운 코드블록 없이 순수 JSON)")

    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.3,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )

    return _parse_json_loose(response.text)
