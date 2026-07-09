# 청아연의원 AI 피부 분석 — 대중용 (Streamlit)

환자가 스마트폰 카메라로 촬영한 얼굴 사진을 업로드하면 Gemini가 피부 상태를 분석해
추천 시술 / 추천 스킨부스터 / 추천 화장품 성분 / 확인되는 피부 병변을 제공하는 대중용 웹앱입니다.

기존 `server.py` + `skin_prescription.html` + `run.bat` (마크뷰 정밀 장비 전용, 병원 내부용 도구)는
그대로 두고, 이 앱은 별도의 신규 파일들로 구성되어 있습니다.

⚠️ **어떤 파일을 실행해야 하나요?**
- `run.bat` 더블클릭 → 옛날 내부용 앱(`server.py` + `skin_prescription.html`, 마크뷰 전용) 실행
- **`run_streamlit.bat` 더블클릭 → 이 문서가 설명하는 새 대중용 앱 실행** (신규 추가 파일)

두 파일은 완전히 별개이며, 새 앱을 쓰려면 반드시 `run_streamlit.bat`을 실행하세요.

## 파일 구성
- `streamlit_app.py` — 메인 앱 (진입점)
- `run_streamlit.bat` — 더블클릭 실행용 (최초 실행 시 패키지 설치 + secrets.toml 생성 안내까지 자동 처리)
- `prompts.py` — 시스템 프롬프트 / 시술 메뉴 / 네이버 리뷰 링크
- `auth.py` — 2주 자동 갱신 비밀번호 로직
- `baumann.py` — 바우만 피부 타입 설문(4축 8문항) 계산 로직
- `gemini_client.py` — Gemini API 호출 (google-genai SDK)
- `secrets_util.py` — secrets.toml이 없을 때도 앱이 죽지 않도록 하는 안전한 접근 헬퍼
- `requirements.txt`
- `.streamlit/secrets.toml.example` — secrets 템플릿

## 로컬 실행
### 방법 1 — 더블클릭 (Windows, 권장)
`run_streamlit.bat`을 더블클릭하세요. 최초 실행 시:
1. `streamlit`이 없으면 `pip install -r requirements.txt`를 자동 실행합니다.
2. `.streamlit/secrets.toml`이 없으면 example을 복사해 메모장으로 열어줍니다 — `GEMINI_API_KEY` 등 값을 채우고 저장 후 메모장을 닫으면 서버가 자동으로 시작됩니다.
3. 브라우저가 자동으로 `http://localhost:8501` 을 엽니다.

### 방법 2 — 커맨드라인
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # 값 채워넣기
streamlit run streamlit_app.py
```
실행 후 터미널에 뜨는 `http://localhost:8501` 주소로 접속하세요 (기존 8765 포트의 내부용 서버와는 별개입니다).

secrets.toml을 아직 채우지 않았어도 앱이 죽지 않고, 사이드바/로그인 화면에 설정 안내 메시지가 표시됩니다.

## Streamlit Cloud 배포
1. 이 폴더를 GitHub 저장소로 push 합니다. (`.streamlit/secrets.toml` 실제 파일은 `.gitignore`로 제외되어 커밋되지 않습니다.)
2. https://share.streamlit.io 에서 "New app" → 저장소 선택 → Main file path에 `streamlit_app.py` 지정.
3. App settings → Secrets 에 `.streamlit/secrets.toml.example` 내용을 참고해 실제 값을 입력:
   - `GEMINI_API_KEY`: https://aistudio.google.com/apikey 에서 발급 (클라우드 배포에서는 필수 — 아래 "AI 인증 방식" 참고)
   - `PASSWORD_SECRET`: 길고 무작위한 문자열 (비밀번호 생성 시드)
   - `ADMIN_KEY`: 관리자 패널 접근 코드 (PASSWORD_SECRET과 다른 값)
   - `GEMINI_MODEL`: 생략 가능 (기본 `gemini-2.5-pro`)
4. Deploy.

## AI 인증 방식 (둘 중 하나)
| 방식 | secrets 설정 | 어디서 동작 | 과금 |
|---|---|---|---|
| Vertex AI | `VERTEX_PROJECT` = Google Cloud 프로젝트 ID | gcloud 로그인된 PC (병원 컴퓨터) | Google Cloud 크레딧 |
| API 키 | `GEMINI_API_KEY` = `AIza...` 키 | 어디서든 (Streamlit Cloud 포함) | AI Studio 키 기준 |

- 둘 다 설정되어 있으면 `VERTEX_PROJECT`(Vertex AI)를 우선 사용합니다.
- **Vertex AI 방식은 Streamlit Cloud에서는 동작하지 않습니다** (클라우드 서버에는 gcloud 로그인이 없음).
  클라우드 배포 시에는 반드시 `GEMINI_API_KEY`를 넣고 `VERTEX_PROJECT`는 빈 값으로 두세요.

## 2주 자동 갱신 비밀번호
- 접속 비밀번호는 재배포 없이 시간이 지나면 자동으로 바뀝니다 (`PASSWORD_SECRET` + 14일 주기 계산, `auth.py`).
- 병원 직원은 앱 좌측 사이드바의 **"🔑 병원 관리자용"** 패널에서 `ADMIN_KEY`를 입력하면
  현재 비밀번호, 적용 기간, 다음 비밀번호를 확인할 수 있습니다. 이 코드를 환자에게 안내하면 됩니다.

## 바우만 피부 타입 설문
- 인적사항 입력 폼 안에 4축(유분/수분, 민감도, 색소침착, 탄력) 8문항의 예/아니오 설문이 포함되어 있습니다 (`baumann.py`).
- 설문은 선택 사항이며, 답변하면 사진 AI 분석과 결합해 바우만 코드(예: OSPW)·타입명·속건조 여부·축별 그래프를 결과 화면에 보여줍니다.
- 설문 결과는 AI 분석 요청 전에 시스템 프롬프트에도 포함되어, 화장품 성분/시술 추천에 반영됩니다.

## 주의 / 참고
- 피부 병변 관련 소견은 참고용 관찰이며 의학적 진단이 아닙니다. 화면 하단에 항상 면책 문구가 표시됩니다.
- 이미지는 전송 전 리사이즈/압축되어 업로드 용량과 API 비용을 줄입니다.
- 마지막에는 네이버 리뷰 페이지로 이동하는 버튼이 항상 노출됩니다.
