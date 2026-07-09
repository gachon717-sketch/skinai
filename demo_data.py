"""결과 화면 미리보기용 샘플 데이터.

로그인 후 주소 뒤에 ?demo=1 을 붙이면 API 호출 없이 이 샘플 결과가 렌더링된다.
디자인 확인, 직원 교육, 다크모드 테스트 용도.
"""

SAMPLE_RESULT = {
    "greeting": "안녕하세요, 청아연의원입니다. 보내주신 사진을 꼼꼼히 살펴보았어요. 전반적으로 잘 관리되고 있는 피부지만, 몇 가지 함께 개선하면 좋을 부분이 보여 안내드립니다.",
    "photo_quality_note": None,
    "skin_scores": {
        "피부톤균일도": 70, "주름개선도": 60, "모공관리도": 55, "피부결매끄러움": 50,
        "유수분밸런스": 55, "홍조안정도": 75, "색소침착도": 80,
    },
    "detected_lesions": [
        {
            "name": "확장된 모공 및 위축성 여드름 흉터",
            "description": "코와 양 볼을 중심으로 모공이 넓어져 있으며, 과거 트러블로 인해 패인 형태의 흉터가 일부 관찰됩니다.",
            "risk_level": "medium",
            "recommendation": "모공 및 흉터 개선을 위한 피부과 시술을 고려해볼 수 있습니다.",
        },
        {
            "name": "작은 점(모반)",
            "description": "우측 뺨에 작은 크기의 점이 관찰되며, 현재 사진상으로는 형태나 색이 균일해 보입니다.",
            "risk_level": "low",
            "recommendation": "크기나 모양, 색의 변화가 느껴진다면 피부과 전문의의 진찰을 받아보시는 것이 좋습니다.",
        },
    ],
    "recommended_treatments": [
        {
            "name": "포텐자",
            "reason": "모공 확장과 위축성 흉터가 주된 고민으로 관찰되어, 마이크로니들 RF로 진피 리모델링을 유도하는 것이 가장 효과적입니다.",
            "expected_effect": "모공 축소, 흉터 완화, 피부결 개선",
            "price_range": "30만원대부터",
            "priority": "high",
        },
        {
            "name": "더마톡신(미라젯 스킨보톡스)",
            "reason": "잔주름과 피지 분비 조절에 도움이 되어 모공 관리와 시너지가 좋습니다.",
            "expected_effect": "잔주름 개선, 피지·모공 조절",
            "price_range": "20만원대부터",
            "priority": "medium",
        },
    ],
    "recommended_boosters": [
        {
            "name": "쥬베룩 스킨부스터 — 미라젯 방식",
            "reason": "콜라겐 재생을 촉진해 피부결 거칠음과 흉터 개선에 적합합니다. 미라젯은 통증 부담을 줄인 분사 방식이라 편하게 받으실 수 있어요.",
            "price_range": "80만원대부터",
        }
    ],
    "recommended_ingredients": [
        {"ingredient": "나이아신아마이드", "reason": "피지 조절과 모공 관리, 피부톤 개선에 도움을 줍니다.", "how_to_use": "저녁 세안 후 세럼 형태로 사용해보세요."},
        {"ingredient": "레티놀", "reason": "피부 재생 주기를 촉진해 피부결과 잔주름 개선에 효과적입니다.", "how_to_use": "주 2-3회 저녁에만, 소량부터 시작하세요."},
        {"ingredient": "히알루론산", "reason": "속건조 보완을 위한 수분 공급에 필수적입니다.", "how_to_use": "토너 직후 촉촉한 상태에서 발라주세요."},
    ],
    "closing_message": "오늘 분석 결과는 참고용이며, 정확한 진단은 내원하셔서 전문의와 상담해보시길 권해드려요. 탄력이나 리프팅이 궁금하시다면 내원 시 편하게 상담을 요청해보세요. 꾸준히 관리하면 분명 좋아질 피부입니다!",
}

SAMPLE_BAUMANN = {
    "code": "OSNW",
    "type_name": "지성 색소 주름형",
    "inner_dry": True,
    "axes": [
        {"label": "유분 / 수분", "pole_left": "지성", "pole_right": "건성", "is_left": True},
        {"label": "민감도", "pole_left": "민감성", "pole_right": "저항성", "is_left": True},
        {"label": "색소침착", "pole_left": "색소침착", "pole_right": "비색소", "is_left": False},
        {"label": "탄력", "pole_left": "주름형", "pole_right": "탄력형", "is_left": True},
    ],
    "desc": "피지 분비가 활발하지만 각질층 수분이 부족한 **속건조 피부**입니다. 겉은 번들거려도 속은 건조하여 자극에 민감하고 화장이 들뜨기 쉽습니다. 외부 자극에 민감하게 반응하는 **민감성** 경향이 있습니다. 탄력 저하와 주름에 주의가 필요합니다.",
    "oily": True, "dry": True, "sens": True, "pig": False, "wri": True,
}
