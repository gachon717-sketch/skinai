"""청아연의원 AI 피부 분석 — 대중용 (스마트폰 카메라 업로드, Streamlit Cloud 배포)"""
import concurrent.futures
import os
import time

import streamlit as st

import auth
import baumann
import prompts
import sheets_log
import stats
from gemini_client import analyze_skin, make_client, prepare_image_bytes
from secrets_util import get_secret, secrets_file_missing

# ── 모드: "clinic"(병원 내 QR, 기본값) / "external"(SNS 공개용) ──
# 우선순위: 진입 파일이 지정한 값(external_app.py) > secrets의 MODE > 기본값 clinic
MODE = os.environ.get("SKINAI_MODE") or get_secret("MODE", "clinic")
IS_EXTERNAL = MODE == "external"
DAILY_LIMIT = int(get_secret("DAILY_LIMIT", "200"))

PAGE_TITLE = "AI 피부 타입 테스트 by 청아연의원" if IS_EXTERNAL else "청아연의원 AI 피부 분석"
st.set_page_config(page_title=PAGE_TITLE, page_icon="🧬" if IS_EXTERNAL else "✨", layout="centered")


def get_src() -> str:
    """유입경로 (?src=youtube 등). 세션에 고정해 rerun에도 유지."""
    if "src" not in st.session_state:
        st.session_state["src"] = st.query_params.get("src", "")
    return st.session_state["src"]

CUSTOM_CSS = """
<style>
:root { --teal: #1B6B5A; --teal-light: #2D8C76; --teal-pale: #E8F5F1; }
.stApp { font-family: 'Noto Sans KR', sans-serif; }
h1, h2, h3 { color: var(--teal); }
div[data-testid="stMetric"] { background: var(--teal-pale); border-radius: 12px; padding: 10px 14px; }
.hero-banner {
  background: var(--teal); color: #fff; padding: 22px 24px; border-radius: 16px;
  margin-bottom: 18px; line-height: 1.7;
}
/* 병변 카드 — 다크모드에서도 읽히도록 글자색을 명시적으로 지정 */
.lesion-high { border-left: 4px solid #D64545; background: #FDECEC; color: #4A1B1B; padding: 12px 14px; border-radius: 8px; margin-bottom: 8px; }
.lesion-medium { border-left: 4px solid #E8A23D; background: #FFF6E8; color: #4A3A16; padding: 12px 14px; border-radius: 8px; margin-bottom: 8px; }
.lesion-low { border-left: 4px solid #8AA8A0; background: #F3F7F6; color: #253531; padding: 12px 14px; border-radius: 8px; margin-bottom: 8px; }
.lesion-high b, .lesion-medium b, .lesion-low b { color: inherit; }
/* 인사말/마무리 말풍선 — 제목이 아닌 본문 크기로 */
.greeting-box {
  background: var(--teal-pale); color: #1F3B33;
  padding: 16px 18px; border-radius: 14px; margin: 4px 0 14px 0;
  font-size: 15px; line-height: 1.8;
}
/* 리뷰 유도 배너 */
.review-banner {
  background: var(--teal-pale); border: 2px solid var(--teal); color: #14453A;
  padding: 18px 20px; border-radius: 14px; margin: 18px 0 10px 0;
  text-align: center; font-size: 16px; line-height: 1.8;
}
</style>
"""
def render_admin_panel():
    with st.sidebar:
        with st.expander("🔑 병원 관리자용"):
            if secrets_file_missing():
                st.warning(
                    "secrets.toml이 아직 설정되지 않았습니다.\n\n"
                    "`.streamlit/secrets.toml.example`을 복사해 `.streamlit/secrets.toml`로 저장하고 "
                    "값을 채운 뒤 앱을 다시 시작하세요."
                )
                return
            admin_key_input = st.text_input("관리자 코드", type="password", key="admin_key_input")
            admin_key = get_secret("ADMIN_KEY")
            if admin_key_input:
                if admin_key and admin_key_input == admin_key:
                    info = auth.current_period_info(get_secret("PASSWORD_SECRET"))
                    st.success(f"현재 접속 비밀번호: **{info['password']}**")
                    st.caption(f"적용 기간: {info['start']} ~ {info['end']}")
                    st.caption(f"다음 비밀번호(예고): {info['next_password']} · {info['next_start']}부터")

                    st.divider()
                    st.markdown("**📈 사용 통계**")
                    s = stats.get_stats()
                    total_a = s.get("analyses", 0)
                    total_r = s.get("review_clicks", 0)
                    total_k = s.get("kakao_clicks", 0)
                    rate = f"{total_r / total_a * 100:.0f}%" if total_a else "-"
                    c1, c2, c3 = st.columns(3)
                    c1.metric("총 분석", f"{total_a}회")
                    c2.metric("리뷰 클릭", f"{total_r}회")
                    c3.metric("카톡 클릭", f"{total_k}회")
                    st.caption(f"리뷰 전환율: {rate}")
                    today = stats.today_stats()
                    today_line = f"오늘: 분석 {today.get('analyses', 0)}회 · 리뷰 {today.get('review_clicks', 0)} · 카톡 {today.get('kakao_clicks', 0)}"
                    if IS_EXTERNAL:
                        today_line += f" (일일 상한 {DAILY_LIMIT}회)"
                    st.caption(today_line)
                    by_src = s.get("by_src", {})
                    if by_src:
                        st.markdown("**유입경로별**")
                        for src_name, counts in by_src.items():
                            st.caption(
                                f"· {src_name}: 분석 {counts.get('analyses', 0)} · "
                                f"카톡 {counts.get('kakao_clicks', 0)} · 리뷰 {counts.get('review_clicks', 0)}"
                            )
                    if sheets_log.enabled():
                        st.caption("🗂 구글 시트 기록: 연결됨")
                    else:
                        st.caption("🗂 구글 시트 기록: 미설정 (서버 재시작 시 위 숫자는 초기화될 수 있음)")
                else:
                    st.error("관리자 코드가 올바르지 않습니다.")


def require_password() -> bool:
    if st.session_state.get("authed"):
        return True

    st.markdown(
        "<div class='hero-banner'><h2 style='color:#fff;margin:0 0 6px 0;'>✨ 청아연의원 AI 피부 분석</h2>"
        "접속 비밀번호는 2주마다 자동으로 갱신됩니다. 병원에서 안내받은 코드를 입력해주세요.</div>",
        unsafe_allow_html=True,
    )

    if secrets_file_missing() or not get_secret("PASSWORD_SECRET"):
        st.info(
            "⚙️ 설정이 아직 완료되지 않았습니다. `.streamlit/secrets.toml` 파일을 열어 "
            "`PASSWORD_SECRET` 등 값을 채운 뒤 앱을 다시 시작해주세요. "
            "(`secrets.toml.example` 참고)"
        )
        st.stop()

    pw = st.text_input("접속 비밀번호", type="password", key="login_pw")
    if st.button("입장하기", type="primary"):
        secret = get_secret("PASSWORD_SECRET")
        if auth.check_password(pw, secret):
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다. 병원에 최신 코드를 문의해주세요.")
    return False


def photo_input(label: str, key: str):
    tab_cam, tab_up = st.tabs(["📷 카메라로 촬영", "🖼️ 갤러리에서 선택"])
    with tab_cam:
        cam = st.camera_input(label, key=f"cam_{key}", label_visibility="collapsed")
    with tab_up:
        up = st.file_uploader(label, type=["jpg", "jpeg", "png"], key=f"up_{key}", label_visibility="collapsed")
    return cam or up


def score_badge(val: int) -> str:
    if val >= 75:
        return "🟢 좋음"
    if val >= 65:
        return "🟡 보통"
    return "🔴 관리 필요"


def render_score_bars(scores: dict):
    st.caption("점수는 0~100점 — **100점에 가까울수록 좋은 상태**입니다. 65점 이하는 집중 관리가 필요한 항목이에요.")

    clean = {name: max(0, min(100, int(val))) for name, val in scores.items()}
    low_items = [f"{name} {val}점" for name, val in clean.items() if val < 65]
    if low_items:
        st.warning("🔴 집중 관리가 필요한 항목: " + " · ".join(low_items))
    else:
        st.success("🟢 모든 항목이 양호한 편이에요!")

    for name, val in clean.items():
        st.write(f"**{name}** — {val}점 · {score_badge(val)}")
        st.progress(val / 100)


def render_lesions(lesions: list):
    if not lesions:
        st.info("사진에서 특이 병변 소견은 확인되지 않았습니다.")
        return
    for item in lesions:
        risk = item.get("risk_level", "low")
        css_class = f"lesion-{risk}" if risk in ("high", "medium", "low") else "lesion-low"
        icon = {"high": "🔴", "medium": "🟠", "low": "⚪"}.get(risk, "⚪")
        st.markdown(
            f"<div class='{css_class}'><b>{icon} {item.get('name','')}</b><br>"
            f"{item.get('description','')}<br>"
            f"<i>권고: {item.get('recommendation','')}</i></div>",
            unsafe_allow_html=True,
        )


def render_treatments(treatments: list):
    if not treatments:
        st.info("현재 특별히 시급한 시술은 없습니다.")
        return
    for t in treatments:
        priority = t.get("priority", "medium")
        badge = "🔥 우선 권장" if priority == "high" else "참고"
        with st.container(border=True):
            st.markdown(f"**{t.get('name','')}** &nbsp; `{badge}`")
            st.write(t.get("reason", ""))
            st.caption(f"기대 효과: {t.get('expected_effect','')}")
            st.caption(f"가격대: {t.get('price_range','')}")


def render_boosters(boosters: list):
    if not boosters:
        st.info("추천 스킨부스터가 없습니다.")
        return
    for b in boosters:
        with st.container(border=True):
            st.markdown(f"**{b.get('name','')}**")
            st.write(b.get("reason", ""))
            st.caption(f"가격대: {b.get('price_range','')}")


def render_ingredients(ingredients: list):
    if not ingredients:
        st.info("추천 성분이 없습니다.")
        return
    for ing in ingredients:
        with st.container(border=True):
            st.markdown(f"**{ing.get('ingredient','')}**")
            st.write(ing.get("reason", ""))
            st.caption(ing.get("how_to_use", ""))


def render_baumann(bdata: dict):
    if not bdata:
        return
    st.markdown("### 🧬 바우만 피부 타입")
    inner_dry_badge = " · 💧 속건조 경향 감지됨" if bdata["inner_dry"] else ""
    st.markdown(f"**{bdata['code']}** — {bdata['type_name']}{inner_dry_badge}")
    for axis in bdata["axes"]:
        value = axis["pole_left"] if axis["is_left"] else axis["pole_right"]
        st.write(f"{axis['label']} — **{value}**")
        st.progress(0.2 if axis["is_left"] else 0.8)
    st.markdown(bdata["desc"])


def render_results(result: dict, bdata: dict = None):
    st.divider()
    greeting = result.get("greeting", "")
    if greeting:
        st.markdown(f"<div class='greeting-box'>💬 {greeting}</div>", unsafe_allow_html=True)
    if result.get("photo_quality_note"):
        st.warning(result["photo_quality_note"])

    st.markdown("### 📊 피부 스코어")
    render_score_bars(result.get("skin_scores", {}))

    render_baumann(bdata)

    lesion_title = "### 🔍 사진에서 참고할 만한 피부 특징" if IS_EXTERNAL else "### 🔍 확인되는 피부 병변"
    st.markdown(lesion_title)
    render_lesions(result.get("detected_lesions", []))

    st.markdown("### 💉 추천 시술")
    render_treatments(result.get("recommended_treatments", []))

    st.markdown("### 💧 추천 스킨부스터")
    render_boosters(result.get("recommended_boosters", []))
    st.caption("💬 표시된 가격은 대략적인 기준이며, 정확한 비용은 상담 시 안내드려요.")

    st.markdown("### 🧴 추천 화장품 성분")
    render_ingredients(result.get("recommended_ingredients", []))

    if result.get("closing_message"):
        st.markdown("---")
        st.markdown(f"*{result['closing_message']}*")

    # CTA — 마무리 인사 직후, 감정이 따뜻할 때 배치 (클릭 집계를 위해 내부 경로 경유)
    src = get_src()
    if IS_EXTERNAL:
        st.markdown(
            "<div class='review-banner'>💬 <b>내 피부, 더 자세히 알고 싶다면?</b><br>"
            "궁금한 점을 카카오톡으로 물어보세요. 청아연의원이 친절하게 안내해드릴게요 😊</div>",
            unsafe_allow_html=True,
        )
        st.link_button("💬 카카오톡으로 상담 문의하기", f"?kakao=go&src={src}", type="primary", use_container_width=True)
        st.caption("분석 결과는 익명 통계로 활용될 수 있습니다. 이름·연락처·사진은 저장되지 않아요.")
    else:
        st.markdown(
            "<div class='review-banner'>💚 <b>오늘 분석, 어떠셨나요?</b><br>"
            "재미있게 보셨다면 리뷰 한 줄 남겨주세요. 원장님과 직원들에게 정말 큰 힘이 됩니다 🙏<br>"
            "<span style='font-size:13px;'>30초면 충분해요!</span></div>",
            unsafe_allow_html=True,
        )
        st.link_button("⭐ 네이버 리뷰 남기러 가기 (클릭!)", f"?review=go&src={src}", type="primary", use_container_width=True)
        st.link_button("💬 카카오톡으로 예약·상담 문의하기", f"?kakao=go&src={src}", use_container_width=True)

    st.caption(prompts.DISCLAIMER)

    if st.button("🔄 다시 분석하기", use_container_width=True):
        st.session_state.pop("result", None)
        st.session_state.pop("baumann", None)
        st.rerun()


def _redirect_out(url: str, label: str):
    """클릭 집계 후 외부 페이지로 자동 이동시키는 공용 처리."""
    st.markdown(f"{label} 페이지로 이동 중입니다... 자동으로 이동하지 않으면 [여기를 눌러주세요]({url}) 🙏")
    import streamlit.components.v1 as components
    # 컴포넌트 iframe은 top 네비게이션이 차단되므로, 같은 출처인 부모 문서에
    # 앵커를 만들어 클릭시키는 방식으로 이동시킨다.
    components.html(
        f"""<script>
        try {{
            var d = window.parent.document;
            var a = d.createElement('a');
            a.href = "{url}";
            a.target = "_self";
            d.body.appendChild(a);
            a.click();
        }} catch (e) {{
            window.open("{url}", "_blank");
        }}
        </script>""",
        height=0,
    )
    st.stop()


def main():
    # CSS는 매 rerun마다 다시 주입해야 한다.
    # (external_app.py가 이 모듈을 import 하는 구조라, 모듈 최상단에 두면 첫 실행 때 한 번만 적용됨)
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    src = st.query_params.get("src", "")

    # 리뷰/카톡 버튼 클릭 집계 후 자동 이동 (로그인 불필요 — 나가는 길목이므로)
    if st.query_params.get("review") == "go":
        stats.increment("review_clicks", src=src)
        sheets_log.log_click("review", src)
        _redirect_out(prompts.NAVER_REVIEW_URL, "⭐ 네이버 리뷰")

    if st.query_params.get("kakao") == "go":
        stats.increment("kakao_clicks", src=src)
        sheets_log.log_click("kakao", src)
        _redirect_out(prompts.KAKAO_CHANNEL_URL, "💬 카카오톡 상담")

    render_admin_panel()

    # 외부 공개 버전은 비밀번호 없이 바로 사용 (일일 상한선으로 비용 방어)
    if not IS_EXTERNAL:
        if not require_password():
            st.stop()

    _ = get_src()  # 유입경로를 세션에 고정

    if IS_EXTERNAL:
        st.markdown(
            "<div class='hero-banner'>"
            "<div style='font-size:13px;letter-spacing:1px;opacity:0.85;margin-bottom:4px;'>청아연의원</div>"
            "<h2 style='color:#fff;margin:0 0 8px 0;'>🧬 AI 피부 타입 테스트</h2>"
            "셀카 한 장이면 AI가 피부 타입과 맞춤 관리 팁을 알려드려요. "
            "재미로 보는 무료 테스트입니다.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='hero-banner'><h2 style='color:#fff;margin:0 0 6px 0;'>✨ 청아연의원 AI 피부 분석</h2>"
            "스마트폰으로 촬영한 얼굴 사진으로 피부 상태를 분석해드립니다. 정면 사진은 필수이며, "
            "측면 사진을 추가하면 정확도가 올라갑니다.</div>",
            unsafe_allow_html=True,
        )

    # 데모 모드: 로그인 후 주소 뒤에 ?demo=1 을 붙이면 샘플 결과 화면 표시 (디자인 확인/직원 교육용)
    if st.query_params.get("demo") == "1":
        import demo_data
        render_results(demo_data.SAMPLE_RESULT, demo_data.SAMPLE_BAUMANN)
        return

    if st.session_state.get("result"):
        render_results(st.session_state["result"], st.session_state.get("baumann"))
        return

    with st.form("intake_form"):
        # ── 1단계: 사진 (핵심 행동을 가장 위로) ──
        st.markdown("#### 📸 1단계 — 정면 사진 (필수)")
        st.info("💡 편하게 찍으셔도 괜찮아요! **정면 한 장이면 충분합니다.** 측면 사진을 추가하거나 안경을 벗고 찍으면 정확도가 조금 더 올라가요.")
        front_file = photo_input("정면 사진", "front")

        with st.expander("➕ 측면 사진 추가하기 (선택, 정확도 향상)"):
            st.markdown("**좌측 사진**")
            left_file = photo_input("좌측 사진", "left")
            st.markdown("**우측 사진**")
            right_file = photo_input("우측 사진", "right")

        st.divider()

        # ── 2단계: 기본 정보 ──
        st.markdown("#### 📝 2단계 — 기본 정보 (선택)")
        col1, col2 = st.columns(2)
        with col1:
            if IS_EXTERNAL:
                name = ""  # 외부 버전은 익명 — 이름을 받지 않음
            else:
                name = st.text_input("이름 (선택)")
            gender = st.segmented_control("성별", ["여", "남"], key="gender_seg")
        with col2:
            age = st.number_input("나이 (선택)", min_value=0, max_value=120, value=0, step=1)
            cosmetics = st.text_input("현재 사용 중인 화장품 (쉼표로 구분, 선택)")

        notes = st.text_area("특이사항 / 주요 피부 고민 (선택)", placeholder="예: 최근 트러블이 심해졌어요, 홍조가 신경쓰여요 등")

        st.divider()

        # ── 3단계: 바우만 설문 ──
        st.markdown("#### 🧬 3단계 — 피부 타입 체크 (바우만 분류, 선택)")
        st.caption("답변하지 않아도 분석은 진행되지만, 답변하시면 사진 분석과 결합해 더 정확한 타입을 알려드려요.")
        baumann_answers = {}
        for group in baumann.QUESTIONS:
            st.markdown(f"**{group['group']}**")
            for item in group["items"]:
                choice = st.segmented_control(item["text"], ["네", "아니오"], key=f"bq_{item['key']}")
                if choice:
                    baumann_answers[item["key"]] = "yes" if choice == "네" else "no"

        submitted = st.form_submit_button("🔬 AI 피부 분석 시작하기", type="primary", use_container_width=True)

    if submitted:
        if not front_file:
            st.error("정면 사진은 필수입니다. 위의 1단계에서 사진을 촬영하거나 선택해주세요.")
            return

        # 외부 공개 버전: 일일 분석 상한 (비용 방어)
        if IS_EXTERNAL and stats.analyses_today() >= DAILY_LIMIT:
            st.warning(
                "🙏 오늘 준비된 무료 분석이 모두 소진되었어요! 내일 다시 찾아와주세요.\n\n"
                "궁금한 점은 카카오톡 채널로 문의하시면 빠르게 안내드릴게요."
            )
            st.link_button("💬 카카오톡으로 문의하기", f"?kakao=go&src={get_src()}", type="primary", use_container_width=True)
            return

        loading_box = st.empty()
        loading_box.info("📷 사진을 준비하고 있어요...")

        photos = {"front": prepare_image_bytes(front_file)}
        if left_file:
            photos["left"] = prepare_image_bytes(left_file)
        if right_file:
            photos["right"] = prepare_image_bytes(right_file)

        gender_code = {"여": "여", "남": "남"}.get(gender, "")
        cosmetics_list = [c.strip() for c in cosmetics.split(",") if c.strip()]

        bdata_pre = baumann.calc_baumann(gender_code, baumann_answers, skin_scores=None)
        baumann_text = baumann.build_prompt_text(bdata_pre)

        system_prompt = prompts.build_system_prompt(
            gender_code, int(age), notes, cosmetics_list, baumann_text=baumann_text, external=IS_EXTERNAL
        )
        model_name = get_secret("GEMINI_MODEL", "gemini-2.5-pro")

        # 단계별 로딩 문구 — API 호출은 백그라운드 스레드에서, 문구는 메인 스레드에서 갱신
        steps = [
            "🔬 사진에서 피부 상태를 살펴보고 있어요...",
            "🧬 피부 타입과 설문 결과를 결합하고 있어요...",
            "💉 맞춤 시술과 성분을 고르고 있어요...",
            "📋 결과지를 작성하고 있어요... 거의 다 됐어요!",
        ]
        try:
            client = make_client()  # secrets 접근은 메인 스레드에서
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(analyze_skin, photos, system_prompt, model_name, client)
                step_idx = 0
                while not future.done():
                    loading_box.info(f"{steps[min(step_idx, len(steps) - 1)]}  (전체 20~40초 정도 걸려요)")
                    step_idx += 1
                    time.sleep(4)
                result = future.result()

            loading_box.empty()
            stats.increment("analyses", src=get_src())
            bdata_final = baumann.calc_baumann(gender_code, baumann_answers, skin_scores=result.get("skin_scores"))
            sheets_log.log_analysis(
                mode=MODE, src=get_src(), gender=gender_code, age=int(age),
                baumann_code=(bdata_final or {}).get("code", ""),
                scores=result.get("skin_scores", {}), notes=notes, result=result,
            )
            st.session_state["result"] = result
            st.session_state["baumann"] = bdata_final
            st.rerun()
        except Exception as e:
            loading_box.empty()
            st.error(f"분석 중 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
