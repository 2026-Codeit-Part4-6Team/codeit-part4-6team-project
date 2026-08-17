from sqlalchemy.orm import Session

from backend.database import create_database_engine
from backend.routers.health_router import is_database_ready


def test_database_readiness_rejects_empty_database():
    """필수 테이블이 없는 DB는 readiness를 통과하지 않습니다."""
    engine = create_database_engine("sqlite:///:memory:")

    with Session(engine) as session:
        assert is_database_ready(session) is False
