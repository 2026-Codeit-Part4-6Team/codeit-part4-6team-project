from __future__ import annotations

import argparse
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

_REQUIRED_ENV = ("OPENAI_API_KEY",)


def missing_required_environment(env: Mapping[str, str]) -> list[str]:
    """Actual 모델 smoke 실행에 반드시 필요한 환경변수를 반환합니다."""
    return [name for name in _REQUIRED_ENV if not env.get(name, "").strip()]


def _request_payload(chatbot_type: str) -> dict[str, Any]:
    if chatbot_type == "basic":
        return {
            "chatbot_type": "basic",
            "question": "직장인 점심 고객을 위한 신메뉴 광고를 만들어줘",
            "platform": "instagram",
            "max_accepted_credits": 0,
        }
    return {
        "chatbot_type": "consultant",
        "question": "직장인 점심 고객을 늘리기 위한 마케팅 전략을 알려줘",
        "max_accepted_credits": 0,
    }


def _run_smoke(chatbots: list[str]) -> int:
    missing = missing_required_environment(os.environ)
    if missing:
        print("missing required environment: " + ", ".join(missing))
        return 2

    # backend.config/backend.database가 import될 때 환경변수를 읽으므로 먼저 고정한다.
    os.environ["CHATBOT_MODE"] = "actual"
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
    os.environ.setdefault("GEOCODE_FALLBACK_ENABLED", "false")

    with tempfile.TemporaryDirectory(prefix="team6-actual-smoke-") as temp_dir:
        db_path = Path(temp_dir) / "actual-smoke.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

        # 환경을 고정한 뒤 import해야 Settings/Engine/Actual client가 올바르게 조립된다.
        from fastapi.testclient import TestClient

        from backend.auth import get_current_user
        from backend.database import SessionLocal, engine
        from backend.init_db import create_tables
        from backend.main import create_app
        from backend.models import User

        create_tables(engine)
        with SessionLocal() as db:
            user = User(
                username="actual-smoke-user",
                password_hash="unused-by-smoke",
                credits=100,
                daily_free_used=0,
                daily_free_reset_at=datetime.now(UTC) + timedelta(hours=12),
                business_name="카페 코드잇",
                business_type="카페",
                address="서울 강남구 테헤란로 123",
                road_address="서울 강남구 테헤란로 123",
                lat=37.5000,
                lng=127.0000,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            app = create_app()
            app.dependency_overrides[get_current_user] = lambda: user
            try:
                with TestClient(app) as client:
                    for chatbot_type in chatbots:
                        response = client.post(
                            "/generate",
                            headers={"Idempotency-Key": str(uuid4())},
                            json=_request_payload(chatbot_type),
                        )
                        body = response.json()
                        print(
                            json.dumps(
                                {
                                    "chatbot_type": chatbot_type,
                                    "http_status": response.status_code,
                                    "response": body,
                                },
                                ensure_ascii=False,
                                indent=2,
                            )
                        )
                        if response.status_code != 200:
                            return 1
                        if body.get("status") not in {"done", "failed"}:
                            return 1
            finally:
                app.dependency_overrides.clear()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Service → Actual Basic/Consultant → ModelResult 로컬 통합 smoke"
    )
    parser.add_argument(
        "--chatbot",
        choices=("basic", "consultant", "both"),
        default="both",
        help="실제 호출할 모델(기본: both)",
    )
    args = parser.parse_args()
    chatbots = ["basic", "consultant"] if args.chatbot == "both" else [args.chatbot]
    return _run_smoke(chatbots)


if __name__ == "__main__":
    raise SystemExit(main())
