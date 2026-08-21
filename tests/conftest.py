import os
from collections.abc import Generator

# backend.config/settings와 backend.database.engine이 import되기 전에 개발 DB를 차단합니다.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.database import create_database_engine, get_db
from backend.init_db import create_tables
from backend.main import create_app


@pytest.fixture
def db_session(tmp_path) -> Generator[Session, None, None]:
    """공용 API 테스트용 tmp_path SQLite Session을 제공합니다."""
    engine = create_database_engine(f"sqlite:///{tmp_path / 'api-test.db'}")
    create_tables(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """개발 DB와 분리된 FastAPI 테스트 클라이언트를 제공합니다."""
    application = create_app()

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(application) as test_client:
            yield test_client
    finally:
        application.dependency_overrides.clear()
