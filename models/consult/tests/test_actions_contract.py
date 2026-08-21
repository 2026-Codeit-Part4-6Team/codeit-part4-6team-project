# models/consult/tests/test_actions_contract.py
"""config.py의 MIN_ACTIONS/MAX_ACTIONS가 서비스 계약과 어긋나지 않는지 확인한다.

주의: backend import는 이 테스트 파일에서만 한다 — 프로덕션 코드가 backend를
import하면 배포 단위 분리(D-031)가 깨진다. 값을 두 곳에 복제해 쓰는 대신,
이 테스트가 한쪽만 바뀌는 드리프트를 잡는다.
"""

from backend.schemas import ConsultantStrategy
from models.consult.config import MAX_ACTIONS, MIN_ACTIONS


def test_action_limits_match_service_schema() -> None:
    meta = ConsultantStrategy.model_fields["actions"].metadata
    assert MIN_ACTIONS == next(m.min_length for m in meta if hasattr(m, "min_length"))
    assert MAX_ACTIONS == next(m.max_length for m in meta if hasattr(m, "max_length"))
