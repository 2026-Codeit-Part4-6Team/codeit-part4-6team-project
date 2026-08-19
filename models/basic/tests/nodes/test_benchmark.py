from unittest.mock import patch

from models.basic.nodes.benchmark_node import benchmark_node

_STORE = {"name": "카페 코드잇", "type": "카페", "lat": 37.5, "lng": 127.0}


@patch("models.basic.nodes.benchmark_node.search_benchmark")
def test_results_found_are_joined_into_benchmark_context(mock_search):
    mock_search.return_value = [
        {"id": "bm_001", "industry": "카페", "copy": "시원한 콜드브루 한 잔"},
        {"id": "bm_002", "industry": "카페", "copy": "향긋한 원두의 아침"},
    ]
    state = {"store": _STORE, "question": "여름 신메뉴 카피 추천해줘"}

    result = benchmark_node(state)

    assert result["context"]["benchmark"] == (
        "업종 벤치마크 카피 예시: 시원한 콜드브루 한 잔; 향긋한 원두의 아침"
    )
    mock_search.assert_called_once_with("카페", k=3)


@patch("models.basic.nodes.benchmark_node.search_benchmark")
def test_no_results_sets_benchmark_to_none(mock_search):
    mock_search.return_value = []
    state = {"store": _STORE, "question": "여름 신메뉴 카피 추천해줘"}

    result = benchmark_node(state)

    assert result["context"]["benchmark"] is None


@patch("models.basic.nodes.benchmark_node.search_benchmark")
def test_missing_store_type_falls_back_to_question_as_query(mock_search):
    mock_search.return_value = []
    store_without_type = {"name": "이름없는가게", "lat": 37.5, "lng": 127.0}
    state = {"store": store_without_type, "question": "겨울 신메뉴 카피 추천해줘"}

    benchmark_node(state)

    mock_search.assert_called_once_with("겨울 신메뉴 카피 추천해줘", k=3)


@patch("models.basic.nodes.benchmark_node.search_benchmark")
def test_existing_context_keys_are_preserved(mock_search):
    mock_search.return_value = []
    state = {
        "store": _STORE,
        "question": "여름 신메뉴 카피 추천해줘",
        "context": {"market": {"info": "상권 데이터"}},
    }

    result = benchmark_node(state)

    assert result["context"]["market"] == {"info": "상권 데이터"}
    assert result["context"]["benchmark"] is None


@patch("models.basic.nodes.benchmark_node.search_benchmark")
def test_search_failure_falls_back_to_none_without_raising(mock_search):
    mock_search.side_effect = RuntimeError("임베딩 모델 로드 실패")
    state = {"store": _STORE, "question": "여름 신메뉴 카피 추천해줘"}

    result = benchmark_node(state)

    assert result["context"]["benchmark"] is None
