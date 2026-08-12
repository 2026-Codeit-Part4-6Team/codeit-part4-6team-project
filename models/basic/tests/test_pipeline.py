from models.basic.graph.build_basic import build_basic_graph
from models.basic.main import assemble_response


def test_e2e_scenarios():
    graph = build_basic_graph()

    store = {
        "name": "카페 코드잇", "type": "카페",
        "address": "서울 강남구 역삼동", "lat": 37.5, "lng": 127.0,
    }

    cases = [
        {
            "label": "A. banner 채널",
            "state": {
                "chatbot_type": "basic", "user_id": 1,
                "question": "여름 신메뉴 홍보 문구 만들어줘",
                "store": store, "platform": "banner", "extra": {},
            },
        },
        {
            "label": "B. 정보 부족 질문 (reask로 바로 끝나야 함)",
            "state": {
                "chatbot_type": "basic", "user_id": 1,
                "question": "광고 만들어줘",
                "store": store, "platform": "instagram", "extra": {},
            },
        },
        {
            "label": "C. 사전 폼 정보 다 채워진 경우",
            "state": {
                "chatbot_type": "basic", "user_id": 1,
                "question": "홍보 문구 만들어줘",
                "store": store, "platform": "instagram",
                "extra": {
                    "purpose": "신메뉴 출시",
                    "price_range": "5000-8000",
                    "target_customer": "20~30대 직장인",
                    "selling_point": "당일 로스팅 원두",
                },
            },
        },
        {
            "label": "D. 되물음 답변으로 채워진 라운드트립 2차 요청",
            "state": {
                "chatbot_type": "basic", "user_id": 1,
                "question": "광고 만들어줘",
                "store": store, "platform": "instagram",
                "extra": {"clarification": "아이스 아메리카노 신메뉴예요"},
            },
        },
    ]

    for case in cases:
        print(f"\n{'='*50}")
        print(case["label"])
        print('='*50)
        final_state = graph.invoke(case["state"])
        response = assemble_response(final_state)
        print(response)