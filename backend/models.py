from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """서비스 소유 ORM의 공통 Base."""


class User(Base):
    """서비스 사용자와 가게 정보를 저장합니다."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(trim(username)) > 0", name="ck_users_username_not_blank"),
        CheckConstraint("lat IS NULL OR lat BETWEEN -90 AND 90", name="ck_users_lat"),
        CheckConstraint("lng IS NULL OR lng BETWEEN -180 AND 180", name="ck_users_lng"),
        CheckConstraint("credits >= 0", name="ck_users_credits"),
        CheckConstraint("daily_free_used >= 0", name="ck_users_daily_free_used"),
        CheckConstraint("api_token_quota >= 0", name="ck_users_api_token_quota"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    road_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    daily_free_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    daily_free_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    api_token_quota: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class Payment(Base):
    """크레딧 결제 이력을 저장합니다."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "idempotency_key", name="uq_payment_user_key"
        ),
        CheckConstraint("amount >= 0", name="ck_payments_amount"),
        CheckConstraint("credits >= 0", name="ck_payments_credits"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    package: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="mock")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class Generation(Base):
    """챗봇 생성 요청과 결과 이력을 저장합니다."""

    __tablename__ = "generations"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_generation_user_key"),
        CheckConstraint(
            "chatbot_type IN ('basic', 'consultant')", name="ck_generations_chatbot_type"
        ),
        CheckConstraint(
            "platform IS NULL OR platform IN ('instagram', 'xbanner')",
            name="ck_generations_platform",
        ),
        CheckConstraint("length(request_hash) = 64", name="ck_generations_request_hash"),
        CheckConstraint("length(trim(question)) > 0", name="ck_generations_question"),
        CheckConstraint("plan IN ('free', 'paid')", name="ck_generations_plan"),
        CheckConstraint("credits_used >= 0", name="ck_generations_credits_used"),
        CheckConstraint("tokens_used >= 0", name="ck_generations_tokens_used"),
        CheckConstraint(
            "status IN ('pending', 'generating', 'done', 'failed', 'published')",
            name="ck_generations_status",
        ),
        CheckConstraint(
            "selected_proposal_index IS NULL OR selected_proposal_index BETWEEN 0 AND 2",
            name="ck_generations_selected_proposal",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_gen_id: Mapped[int | None] = mapped_column(
        ForeignKey("generations.id"), nullable=True
    )
    chatbot_type: Mapped[str] = mapped_column(String(20), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(36), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(20), nullable=True)
    copy_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_b64: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(String(10), nullable=False)
    credits_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    hitl_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    selected_proposal_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )


class WaitingCopy(Base):
    """생성 대기 화면에 표시할 문구를 저장합니다."""

    __tablename__ = "waiting_copies"
    __table_args__ = (
        CheckConstraint("length(trim(copy_text)) > 0", name="ck_waiting_copy_not_blank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    copy_text: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.current_timestamp()
    )
