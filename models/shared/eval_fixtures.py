# models/shared/eval_fixtures.py — 골든 데이터셋 평가 공통 입력 (관리: 전민재 PM)
"""문항마다 반복되는 값을 한 곳에 둔다.

가게 정보를 바꿔야 할 때 60개 문항이 아니라 이 파일 한 곳만 고친다.
문항에 store 를 따로 적은 경우에만 그 값이 우선한다.
"""

EVAL_USER_ID = 1

DEFAULT_STORE = {
    "name": "카페 코드잇",
    "type": "카페",
    "address": "서울 강남구 역삼동",
    "lat": 37.4979,
    "lng": 127.0276,
}


def build_model_request(item: dict) -> dict:
    """골든 문항 1건을 ModelRequest 형태의 dict 로 조립한다.

    input 은 부분 입력이므로 question·user_id·store 를 여기서 주입한다.
    platform 규칙(basic 필수 / consultant 는 null)도 여기서 강제해
    문항 작성자가 실수해도 스키마 검증에서 깨지지 않게 한다.
    """
    raw = item.get("input") or {}

    chatbot_type = raw.get("chatbot_type") or (
        "consultant" if item["area"] == "consult" else "basic"
    )

    if chatbot_type == "consultant":
        platform = None                      # 계약상 consultant 는 platform 을 쓰지 않는다
    else:
        platform = raw.get("platform") or "instagram"

    return {
        "chatbot_type": chatbot_type,
        "user_id": raw.get("user_id", EVAL_USER_ID),
        "question": item["question"],
        "platform": platform,
        "store": raw.get("store", DEFAULT_STORE),
        "extra": raw.get("extra"),
    }