# from models.basic.graph.build_basic import build_basic_graph
# from models.basic.main import assemble_response


# def test_e2e_scenarios():
#     graph = build_basic_graph()

#     store = {
#         "name": "카페 코드잇",
#         "type": "카페",
#         "address": "서울 강남구 역삼동",
#         "lat": 37.5,
#         "lng": 127.0,
#     }

#     cases = [
#         {
#             "label": "A. banner 채널",
#             "state": {
#                 "chatbot_type": "basic",
#                 "user_id": 1,
#                 "question": "여름 신메뉴 홍보 문구 만들어줘",
#                 "store": store,
#                 "platform": "banner",
#                 "extra": {},
#             },
#         },
#         {
#             "label": "B. 정보 부족 질문 (reask로 바로 끝나야 함)",
#             "state": {
#                 "chatbot_type": "basic",
#                 "user_id": 1,
#                 "question": "광고 만들어줘",
#                 "store": store,
#                 "platform": "instagram",
#                 "extra": {},
#             },
#         },
#         {
#             "label": "C. 사전 폼 정보 다 채워진 경우",
#             "state": {
#                 "chatbot_type": "basic",
#                 "user_id": 1,
#                 "question": "홍보 문구 만들어줘",
#                 "store": store,
#                 "platform": "instagram",
#                 "extra": {
#                     "purpose": "신메뉴 출시",
#                     "price_range": "5000-8000",
#                     "target_customer": "20~30대 직장인",
#                     "selling_point": "당일 로스팅 원두",
#                 },
#             },
#         },
#         {
#             "label": "D. 되물음 답변으로 채워진 라운드트립 2차 요청",
#             "state": {
#                 "chatbot_type": "basic",
#                 "user_id": 1,
#                 "question": "광고 만들어줘",
#                 "store": store,
#                 "platform": "instagram",
#                 "extra": {"clarification": "아이스 아메리카노 신메뉴예요"},
#             },
#         },
#     ]

#     for case in cases:
#         print(f"\n{'='*50}")
#         print(case["label"])
#         print("=" * 50)
#         final_state = graph.invoke(case["state"])
#         response = assemble_response(final_state)
#         print(response)


import json
from unittest.mock import patch

import pytest

from models.basic.graph.build_basic import build_basic_graph
from models.basic.main import assemble_response

_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.5,
    "lng": 127.0,
}


def _fake_call_llm(system: str, user: str, json_mode: bool = False) -> tuple[str, int]:
    """question_analysis/copy_gen/ranking 세 노드가 공유하는 call_llm을 시스템
    프롬프트 내용으로 구분해 노드별 응답 스키마에 맞는 고정 응답을 돌려준다."""
    payload = json.loads(user)

    if "카피라이터" in system:
        content = json.dumps(
            {
                "candidates": [
                    "여름 신메뉴, 지금 만나보세요",
                    "오늘의 특별함을 담은 한 잔",
                    "당신의 하루를 채우는 맛",
                ]
            }
        )
        return content, 10

    if "심사위원" in system:
        ranked = [{"copy": c, "score": 4.0} for c in payload["candidate"]]
        return json.dumps({"ranked": ranked}), 10

    if "분석하는 어시스턴트" in system:
        question = payload["question"]
        extra = payload.get("extra") or {}
        if question == "광고 만들어줘" and not extra:
            content = json.dumps(
                {
                    "sufficient": False,
                    "rewritten_question": question,
                    "message": "무엇을 광고하고 싶으신지 조금 더 알려주세요.",
                }
            )
        else:
            content = json.dumps(
                {"sufficient": True, "rewritten_question": question, "message": ""}
            )
        return content, 10

    raise AssertionError(f"예상치 못한 system prompt: {system[:30]}")


def _fake_get_market(lat, lng, radius=500, industry=None):
    return {"total_count": 43, "same_industry_count": 2, "nearest_distance_m": 80}


def _fake_get_trend(question, industry=None):
    return {
        "keyword": industry or "카페",
        "direction": "상승",
        "related": ["아이스 아메리카노"],
        "weather": None,
    }


@pytest.fixture(autouse=True)
def _mock_external_calls():
    """외부 API(OpenAI, 상권/트렌드 API)를 모두 모킹해 e2e 테스트를 CI에서도
    네트워크/크리덴셜 없이 실행 가능하게 한다. 나머지 의존성(check_input/
    check_output/self_check/check_regulation/generate_image/search_benchmark)은
    현재 전부 D1 스텁이라 모킹 없이도 예외 없이 통과한다."""
    with (
        patch(
            "models.basic.nodes.question_analysis.call_llm", side_effect=_fake_call_llm
        ),
        patch("models.basic.nodes.copy_gen.call_llm", side_effect=_fake_call_llm),
        patch("models.basic.nodes.ranking.call_llm", side_effect=_fake_call_llm),
        patch(
            "models.basic.nodes.market_for_copy.get_market",
            side_effect=_fake_get_market,
        ),
        patch(
            "models.basic.nodes.trend_for_copy.get_trend", side_effect=_fake_get_trend
        ),
    ):
        yield


def test_e2e_scenario_a_banner_channel():
    graph = build_basic_graph()
    final_state = graph.invoke(
        {
            "chatbot_type": "basic",
            "user_id": 1,
            "question": "여름 신메뉴 홍보 문구 만들어줘",
            "store": _STORE,
            "platform": "banner",
            "extra": {},
        }
    )
    response = assemble_response(final_state)
    assert response["status"] == "ok"
    assert len(response["proposals"]) == 3


def test_e2e_scenario_b_insufficient_info_reasks():
    graph = build_basic_graph()
    final_state = graph.invoke(
        {
            "chatbot_type": "basic",
            "user_id": 1,
            "question": "광고 만들어줘",
            "store": _STORE,
            "platform": "instagram",
            "extra": {},
        }
    )
    response = assemble_response(final_state)
    assert response["status"] == "blocked"
    assert response["action"] == "reask"


def test_e2e_scenario_c_form_prefilled():
    graph = build_basic_graph()
    final_state = graph.invoke(
        {
            "chatbot_type": "basic",
            "user_id": 1,
            "question": "홍보 문구 만들어줘",
            "store": _STORE,
            "platform": "instagram",
            "extra": {
                "purpose": "신메뉴 출시",
                "price_range": "5000-8000",
                "target_age": "20~30대 직장인",
                "strength": "당일 로스팅 원두",
            },
        }
    )
    response = assemble_response(final_state)
    assert response["status"] == "ok"


def test_e2e_scenario_d_clarification_round_trip():
    graph = build_basic_graph()
    final_state = graph.invoke(
        {
            "chatbot_type": "basic",
            "user_id": 1,
            "question": "광고 만들어줘",
            "store": _STORE,
            "platform": "instagram",
            "extra": {"clarification": "아이스 아메리카노 신메뉴예요"},
        }
    )
    response = assemble_response(final_state)
    assert response["status"] == "ok"
