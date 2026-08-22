from typing import NotRequired

from models.shared.state_common import CommonState


class BasicState(CommonState):
    """기본 카피/이미지 생성 파이프라인 전용 상태.

    공통 상태(CommonState)에 카피 후보·랭킹·이미지 생성/검수 결과와
    재시도 루프에 필요한 필드를 추가한다.
    """

    keyword: NotRequired[str]  # question_analysis가 추출한 트렌드 검색용 키워드
    copy_candidates: NotRequired[list]  # 3안 후보, [{"copy": "..."}]
    ranked_copies: NotRequired[
        list
    ]  # LLM judge 랭킹 결과, [{"copy": "...", "score": 4.3, "image_b64": "...", "image_prompt": "..."}]
    image_results: NotRequired[list]  # base64 이미지만 모은 리스트
    image_prompts: NotRequired[
        list
    ]  # 이미지 생성 프롬프트, ranked_copies와 같은 인덱스로 정렬됨
    image_review_result: NotRequired[
        dict
    ]  # CLIP Score, 금지요소 검수 결과 (validation과 별도)

    copy_retry_count: NotRequired[int]  # 카피 생성 / 규제 재시도 루프 카운터
    image_retry_count: NotRequired[int]  # 이미지 재생성 루프 카운터
    status: NotRequired[str]  # ok, blocked, error
    issues: NotRequired[
        list[dict]
    ]  # [{"source": ..., "action": "block"/"reask"/"warn", "reason": ..., "message": ...}, ...]
