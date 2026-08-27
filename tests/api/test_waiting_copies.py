from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.models import User, WaitingCopy
from backend.routers import waiting_router


def add_user(db: Session, *, business_type="카페") -> User:
    user = User(
        username="waiting-user",
        password_hash="unused",
        credits=100,
        business_name="카페 코드잇",
        business_type=business_type,
        address="서울 강남구",
        lat=37.5,
        lng=127.0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_as(client: TestClient, user: User) -> None:
    client.app.dependency_overrides[get_current_user] = lambda: user


def test_waiting_copy_requires_authentication(client: TestClient):
    assert client.get("/waiting-copies").status_code == 401


def test_waiting_copy_prefers_the_users_business_type(
    client: TestClient, db_session: Session
):
    user = add_user(db_session, business_type="카페")
    db_session.add_all(
        [
            WaitingCopy(copy_text="식당 문구", industry="식당"),
            WaitingCopy(copy_text="카페 문구", industry="카페"),
        ]
    )
    db_session.commit()
    auth_as(client, user)

    response = client.get("/waiting-copies")

    assert response.status_code == 200
    assert response.json()["copy_text"] == "카페 문구"
    assert response.json()["industry"] == "카페"


def test_waiting_copy_uses_bounded_primary_key_offset(monkeypatch, client, db_session):
    user = add_user(db_session, business_type="카페")
    db_session.add_all(
        [
            WaitingCopy(copy_text="카페 문구 1", industry="카페"),
            WaitingCopy(copy_text="카페 문구 2", industry="카페"),
            WaitingCopy(copy_text="전체 문구", industry="식당"),
        ]
    )
    db_session.commit()
    auth_as(client, user)
    bounds = []

    def choose_last(upper_bound):
        bounds.append(upper_bound)
        return upper_bound - 1

    monkeypatch.setattr(waiting_router, "randrange", choose_last)

    response = client.get("/waiting-copies")

    assert response.status_code == 200
    assert response.json()["copy_text"] == "카페 문구 2"
    assert bounds == [2]


def test_waiting_copy_falls_back_to_global_copy(
    client: TestClient, db_session: Session
):
    user = add_user(db_session, business_type="미용실")
    copy = WaitingCopy(copy_text="공통 문구", industry=None)
    db_session.add(copy)
    db_session.commit()
    db_session.refresh(copy)
    auth_as(client, user)

    response = client.get("/waiting-copies")

    assert response.status_code == 200
    assert response.json() == {
        "id": copy.id,
        "copy_text": "공통 문구",
        "industry": None,
    }


def test_waiting_copy_returns_503_when_table_is_empty(
    client: TestClient, db_session: Session
):
    user = add_user(db_session)
    auth_as(client, user)

    response = client.get("/waiting-copies")

    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "waiting_copy_unavailable"
