from typing import NotRequired

from models.shared.state_common import CommonState

class BasicState(CommonState):

    copy_candidates: NotRequired[list]       # 3안 후보, [{"copy": "..."}]
    ranked_copies: NotRequired[list]         # LLM judge 랭킹 결과, [{"copy": "...", "score": 4.3, "image_b64": "..."}]

    image_results: NotRequired[list]         # base64 이미지만 모은 리스트
    image_review_result: NotRequired[dict]   # CLIP Score, 금지요소 검수 결과 (validation과 별도)

    retry_count: NotRequired[int]            # 재생성 루프 카운터
    status: NotRequired[str]                 # ok, blocked, error
    issues: NotRequired[list[dict]]          # [{"source": ..., "action": "block"/"reask"/"warn", "reason": ..., "message": ...}, ...]