# 컨설팅 결과 → DB 저장 → source_context 복원까지의 왕복 계약 테스트(D8, D-365)
#
# [이 전략으로 광고 만들기] 버튼은 컨설팅 시점이 아니라 며칠 뒤 눌린다 — 그 사이
# DB에 저장된 Consultant 결과가 sources/reasons가 비었거나 actions가 1~3개를
# 벗어나면, 생성 시점엔 조용히 통과했다가 버튼을 누르는 순간
# backend.services.generation_service._resolve_source_context()의 재검증에서
# GenerationDataInvariantError(서비스 쪽 500)로 터진다. 이 파일은 그 왕복을 고정한다.
#
# LLM 모델 호출은 0회다(call_llm을 mock). models/consult/tests/에서 backend를
# import하는 건 배포 단위 분리 원칙의 예외로 테스트 파일에 한해 허용된다(D-210).
import json
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.init_db import create_tables
from backend.models import Generation, User
from backend.schemas import GenerateRequest
from backend.services.generation_service import (
    GenerationDataInvariantError,
    build_model_request,
    hash_generate_request,
)
from models.consult.main import run

_STORE = {"name": "카페 코드잇", "type": "카페", "address": "서울 강남구 역삼동", "lat": 37.5, "lng": 127.0}


def _make_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'roundtrip.db'}")
    create_tables(engine)
    return engine


def _add_user(db: Session) -> User:
    user = User(
        username="roundtrip-user",
        password_hash="hash",
        credits=100,
        business_name=_STORE["name"],
        business_type=_STORE["type"],
        address=_STORE["address"],
        road_address=_STORE["address"],
        lat=_STORE["lat"],
        lng=_STORE["lng"],
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _consultant_request() -> GenerateRequest:
    return GenerateRequest.model_validate(
        {
            "chatbot_type": "consultant",
            "question": "상권 전략을 알려줘",
            "platform": None,
            "max_accepted_credits": 10,
        }
    )


def _basic_request(source_gen_id: int) -> GenerateRequest:
    return GenerateRequest.model_validate(
        {
            "chatbot_type": "basic",
            "question": "이 전략으로 광고 만들어줘",
            "platform": "instagram",
            "max_accepted_credits": 0,
            "source_gen_id": source_gen_id,
        }
    )


def _add_generation(db: Session, user: User, *, result_json: str) -> Generation:
    request = _consultant_request()
    generation = Generation(
        user_id=user.id,
        chatbot_type="consultant",
        idempotency_key="00000000-0000-0000-0000-000000000001",
        request_hash=hash_generate_request(request),
        question=request.question,
        platform=request.platform,
        plan="free",
        credits_used=0,
        status="done",
        result_json=result_json,
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    return generation


@patch("models.consult.nodes.strategy.call_llm")
@patch("models.consult.nodes.suggested_chips.call_llm")
@patch("models.consult.nodes.question_analysis.call_llm")
@patch("models.consult.nodes.trend_for_consult.get_trend")
@patch("models.consult.nodes.market_for_consult.get_market")
def _run_consult_model(mock_get_market, mock_get_trend, mock_qa, mock_chips, mock_strategy) -> dict:
    """실제 그래프를 mock LLM으로 실행해 assemble_response()가 만드는 진짜 ok 결과를 얻는다.

    get_market()/get_trend()도 mock한다 — 안 하면 실 API 키가 설정된 환경에서
    실제 상권 API·캐시 DB에 접근해 이 테스트가 환경 의존적이고 느려진다(Codex 리뷰)."""
    mock_get_market.return_value = None
    mock_get_trend.return_value = None
    mock_qa.return_value = (
        json.dumps(
            {"rewritten_question": "상권 전략을 알려줘", "is_sufficient": True, "missing_info": [], "keyword": None}
        ),
        100,
    )
    mock_chips.return_value = (json.dumps({"chips": ["질문 1", "질문 2", "질문 3"]}), 50)
    mock_strategy.return_value = (
        json.dumps(
            {
                "title": "상권 전략",
                "summary": "점심 직장인 타깃",
                "actions": [{"type": "target", "content": "직장인 메시지를 강화합니다."}],
                "reasons": ["오피스 상권"],
            }
        ),
        100,
    )
    return run(
        {
            "chatbot_type": "consultant",
            "user_id": 1,
            "question": "상권 전략을 알려줘",
            "store": _STORE,
        }
    )


def test_real_consult_result_round_trips_through_source_context(tmp_path):
    """정상 케이스 — 실제 컨설턴트 모델 출력이 DB 저장→복원까지 깨지지 않는다."""
    result = _run_consult_model()
    assert result["status"] == "ok"

    engine = _make_engine(tmp_path)
    with Session(engine) as db:
        user = _add_user(db)
        source = _add_generation(db, user, result_json=json.dumps(result, ensure_ascii=False))

        model_request = build_model_request(db, user, _basic_request(source.id))

        assert model_request.source_context is not None
        assert model_request.source_context.strategy.summary == result["strategy"]["summary"]
        assert [a.model_dump() for a in model_request.source_context.strategy.actions] == result["strategy"]["actions"]
        assert model_request.source_context.reasons == result["reasons"]
        assert model_request.source_context.sources == result["sources"]


def _payload(**overrides) -> dict:
    base = {
        "status": "ok",
        "title": "상권 전략",
        "strategy": {"summary": "점심 직장인 타깃", "actions": [{"type": "target", "content": "직장인 메시지를 강화합니다."}]},
        "reasons": ["오피스 상권"],
        "sources": ["상권분석"],
        "tokens_used": 7,
        "suggested_chips": ["질문 1", "질문 2", "질문 3"],
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("label", "overrides"),
    [
        ("sources 빈 배열", {"sources": []}),
        ("reasons 빈 배열", {"reasons": []}),
        (
            "actions 0개",
            {"strategy": {"summary": "점심 직장인 타깃", "actions": []}},
        ),
        (
            "actions 4개(3개 초과)",
            {
                "strategy": {
                    "summary": "점심 직장인 타깃",
                    "actions": [{"type": "target", "content": f"액션 {i}"} for i in range(4)],
                }
            },
        ),
    ],
)
def test_invariant_violation_surfaces_as_server_error_at_button_click_time(tmp_path, label, overrides):
    """sources/reasons가 비거나 actions가 1~3개를 벗어나면, 생성 시점이 아니라
    (며칠 뒤를 흉내낸) 버튼 클릭 시점의 재검증에서 GenerationDataInvariantError로
    터진다 — 생성 시점엔 이 malformed 결과가 이미 "done"으로 저장돼 있다는
    전제라 여기서 재현하는 건 저장 이후 시점의 재검증 실패다."""
    engine = _make_engine(tmp_path)
    with Session(engine) as db:
        user = _add_user(db)
        source = _add_generation(db, user, result_json=json.dumps(_payload(**overrides), ensure_ascii=False))

        with pytest.raises(GenerationDataInvariantError):
            build_model_request(db, user, _basic_request(source.id))
