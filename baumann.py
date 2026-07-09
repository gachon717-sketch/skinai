"""바우만 피부 타입 주관식 설문 + 계산 로직.

skin_prescription.html 의 calcBaumann()/getBaumannPromptText() 를 그대로 Python으로 이식.
주관식 설문(8문항, 4축) + AI가 사진에서 뽑은 skin_scores 를 결합해 최종 타입을 판정한다.
"""
from typing import Optional

QUESTIONS = [
    {
        "group": "💧 유분 / 수분",
        "items": [
            {"key": "oily", "text": "평소 피부가 번들거리나요?"},
            {"key": "dry", "text": "세안 후 피부가 당기거나 건조함을 느끼나요?"},
        ],
    },
    {
        "group": "🔴 민감도",
        "items": [
            {"key": "sens1", "text": "새로운 화장품 사용 시 자극이나 붉어짐이 쉽게 생기나요?"},
            {"key": "sens2", "text": "계절 변화나 날씨에 피부가 쉽게 반응하나요?"},
        ],
    },
    {
        "group": "🟤 색소침착",
        "items": [
            {"key": "pig1", "text": "햇빛 노출 후 색소(기미·잡티)가 잘 생기나요?"},
            {"key": "pig2", "text": "여드름이나 상처 후 색소침착이 잘 생기나요?"},
        ],
    },
    {
        "group": "〰️ 탄력",
        "items": [
            {"key": "wri1", "text": "표정 지을 때 눈가·입가에 주름이 생기나요?"},
            {"key": "wri2", "text": "피부가 탄력을 잃고 처진 느낌이 드나요?"},
        ],
    },
]

TYPE_NAMES = {
    "OSPW": "민감성 지성 주름형", "OSPT": "민감성 지성 탄력형",
    "OSNW": "지성 색소 주름형", "OSNT": "지성 색소 탄력형",
    "ORPW": "저항성 지성 주름형", "ORPT": "저항성 지성 탄력형",
    "ORNW": "지성 중성 주름형", "ORNT": "가장 이상적인 지성 피부",
    "DSPW": "민감성 건성 주름형", "DSPT": "민감성 건성 탄력형",
    "DSNW": "건성 색소 주름형", "DSNT": "건성 색소 탄력형",
    "DRPW": "저항성 건성 주름형", "DRPT": "저항성 건성 탄력형",
    "DRNW": "건성 중성 주름형", "DRNT": "가장 이상적인 건성 피부",
}


def calc_baumann(gender: str, answers: dict, skin_scores: Optional[dict] = None) -> Optional[dict]:
    """answers: {"oily": "yes"/"no", ...}. 답변이 하나도 없으면 None 반환."""
    if not answers:
        return None

    oily = answers.get("oily") == "yes"
    dry = answers.get("dry") == "yes"
    sens = answers.get("sens1") == "yes" or answers.get("sens2") == "yes"
    pig = answers.get("pig1") == "yes" or answers.get("pig2") == "yes"
    wri = answers.get("wri1") == "yes" or answers.get("wri2") == "yes"

    scores = skin_scores or {}
    nl_wrinkle = scores.get("주름개선도", 70) < 65
    nl_texture = scores.get("피부결매끄러움", 70) < 65
    uv_pigsebum = scores.get("유수분밸런스", 70) < 60

    inner_dry = False
    if oily and dry:
        inner_dry = True
    elif dry and (nl_wrinkle or nl_texture) and uv_pigsebum:
        inner_dry = True
    elif gender == "여" and dry and (nl_wrinkle or nl_texture):
        inner_dry = True

    code = ("O" if oily else "D") + ("S" if sens else "R") + ("P" if pig else "N") + ("W" if wri else "T")
    type_name = TYPE_NAMES.get(code, f"{code} 타입")

    axes = [
        {"label": "유분 / 수분", "pole_left": "지성", "pole_right": "건성", "is_left": oily},
        {"label": "민감도", "pole_left": "민감성", "pole_right": "저항성", "is_left": sens},
        {"label": "색소침착", "pole_left": "색소침착", "pole_right": "비색소", "is_left": pig},
        {"label": "탄력", "pole_left": "주름형", "pole_right": "탄력형", "is_left": wri},
    ]

    if inner_dry:
        if oily:
            desc = "피지 분비가 활발하지만 각질층 수분이 부족한 **속건조 피부**입니다. 겉은 번들거려도 속은 건조하여 자극에 민감하고 화장이 들뜨기 쉽습니다."
        else:
            desc = "피부 표면과 각질층 모두 수분이 부족한 **속건조 건성 피부**입니다. 충분한 보습이 최우선입니다."
    elif oily:
        desc = "피지 분비가 왕성한 지성 피부입니다. 모공 관리와 유·수분 밸런스 조절이 핵심입니다."
    else:
        desc = "수분과 피지 모두 부족한 건성 피부입니다. 보습막 강화와 수분 공급이 가장 중요합니다."

    if sens:
        desc += " 외부 자극에 민감하게 반응하는 **민감성** 경향이 있습니다."
    if pig:
        desc += " 색소침착이 잘 생기는 편이므로 **자외선 차단**이 필수입니다."
    if wri:
        desc += " 탄력 저하와 주름에 주의가 필요합니다."

    return {
        "code": code, "type_name": type_name, "inner_dry": inner_dry, "axes": axes, "desc": desc,
        "oily": oily, "dry": dry, "sens": sens, "pig": pig, "wri": wri,
    }


def build_prompt_text(bdata: Optional[dict]) -> str:
    """분석 요청 전 시스템 프롬프트에 삽입할 주관식 설문 결과 텍스트."""
    if not bdata:
        return ""
    inner_dry_text = ""
    if bdata["inner_dry"]:
        oil_state = "과다" if bdata["oily"] else "정상"
        inner_dry_text = (
            f"\n⚠️ 속건조 피부 감지: 피지는 {oil_state}이지만 각질층 수분 부족. "
            "화장품 성분 추천 및 피부 설명에 '속건조'를 자연스럽게 포함할 것."
        )
    return f"""
【바우만 피부 타입 (주관적 설문 결과)】
타입 코드: {bdata['code']} ({bdata['type_name']})
- 유분/수분: {'지성(O)' if bdata['oily'] else '건성(D)'}
- 민감도: {'민감성(S)' if bdata['sens'] else '저항성(R)'}
- 색소: {'색소침착(P)' if bdata['pig'] else '비색소(N)'}
- 탄력: {'주름형(W)' if bdata['wri'] else '탄력형(T)'}{inner_dry_text}

위 설문 결과를 스마트폰 사진 분석과 통합하여 해석하세요.
속건조 피부인 경우 greeting, closing_message, recommended_ingredients 의 설명에 "속건조" 특성을 자연스럽게 녹여 표현하세요.
"속건조 타입입니다"처럼 단독으로 표기하지 말고, 피부 상태 설명 안에 자연스럽게 포함하세요."""
