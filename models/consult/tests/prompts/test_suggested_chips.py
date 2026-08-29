# models/consult/prompts/suggested_chips.py 테스트 — 칩의 화자 방향(사용자→챗봇)이
# 프롬프트에 명시돼 있는지 확인한다. 2026-08-24 10문항 라이브 파일럿에서 전 문항
# 전체 칩이 "챗봇이 사용자에게 되묻는" 방향으로 뒤집혀 나온 것을 근거로 삼는다.
from models.consult.prompts.suggested_chips import SYSTEM_PROMPT, build_user_prompt

_STORE = {"name": "역전분식", "type": "분식집", "address": "인천 부평구 부평동"}


def test_system_prompt_states_chips_are_sent_as_users_next_message() -> None:
    assert "사용자의 다음 메시지로" in SYSTEM_PROMPT


def test_system_prompt_forbids_chatbot_asking_user_direction() -> None:
    assert "되묻는 문장은 절대 만들지 않는다" in SYSTEM_PROMPT


def test_system_prompt_missing_info_instruction_asks_how_not_what() -> None:
    """구 버전 문구("그 정보를 채우는 질문")는 방향을 명시하지 않아 챗봇이 사용자에게
    값을 되묻는 형태로 새는 원인이었다(missing_info가 없는 문항에서도 역전이 났으므로
    이 문구 하나만의 문제는 아니지만, 이 문구부터 방향을 명시하도록 고친다)."""
    assert "그 정보의 값을 묻지" in SYSTEM_PROMPT
    assert "그 정보를 채우는 질문으로 만든다" not in SYSTEM_PROMPT


def test_system_prompt_has_forbidden_vs_allowed_direction_examples() -> None:
    """2026-08-24 파일럿에서 실제로 나온 역방향 문장("주요 타겟 고객층은 누구인가요?")을
    금지 예시로 그대로 고정해, 같은 문장이 다시 나오면 예시와 모순되게 한다."""
    assert '금지: "주요 타겟 고객층은 누구인가요?"' in SYSTEM_PROMPT
    assert '허용: "우리 가게의 타겟 고객층을 어떻게 정하면 좋을까요?"' in SYSTEM_PROMPT


def test_build_user_prompt_unaffected_by_direction_wording_change() -> None:
    result = build_user_prompt("홍보 방법이 궁금해요", _STORE, [])

    assert '질문: "홍보 방법이 궁금해요"' in result
    assert "부족한 정보" not in result
