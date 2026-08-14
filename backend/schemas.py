import logging
from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)

ChatbotType = Literal["basic", "consultant"]
Platform = Literal["instagram", "banner"]
GenerationStatus = Literal["pending", "generating", "done", "failed", "published"]


class StrictModel(BaseModel):
    """정의되지 않은 필드를 거부하는 계약 모델."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class InboundModel(BaseModel):
    """모델이 추가한 최상위 필드를 관측하며 무시하는 입력 계약 모델."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _log_ignored_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            known = set(cls.model_fields)
            known.update(
                field.alias for field in cls.model_fields.values() if field.alias
            )
            ignored = set(data) - known
            if ignored:
                logger.info(
                    "%s: 모델 응답의 미정의 필드를 무시했습니다: %s",
                    cls.__name__,
                    sorted(ignored),
                )
        return data


class PreviewGenerateRequest(StrictModel):
    """초기 컨테이너 연결 검증용 생성 요청."""

    prompt: str = Field(min_length=1, max_length=2_000)


class RegisterRequest(StrictModel):
    """서비스 회원가입 요청."""

    username: str = Field(min_length=3, max_length=100)
    password: SecretStr
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    business_name: str = Field(min_length=1, max_length=200)
    business_type: str = Field(min_length=1, max_length=100)
    address: str = Field(min_length=1, max_length=500)
    address_detail: str | None = Field(default=None, max_length=500)

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        """사용자명의 공백과 대소문자를 정규화합니다."""
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: SecretStr) -> SecretStr:
        """bcrypt가 허용하는 UTF-8 바이트 길이를 검증합니다."""
        length = len(value.get_secret_value().encode("utf-8"))
        if not 8 <= length <= 72:
            raise ValueError("비밀번호는 UTF-8 기준 8~72바이트여야 합니다.")
        return value


class LoginRequest(StrictModel):
    """서비스 로그인 요청."""

    username: str = Field(min_length=3, max_length=100)
    password: SecretStr

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value: object) -> object:
        """로그인 사용자명을 회원가입과 같은 방식으로 정규화합니다."""
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: SecretStr) -> SecretStr:
        """bcrypt가 허용하는 UTF-8 바이트 길이를 검증합니다."""
        length = len(value.get_secret_value().encode("utf-8"))
        if not 8 <= length <= 72:
            raise ValueError("비밀번호는 UTF-8 기준 8~72바이트여야 합니다.")
        return value


class UserResponse(StrictModel):
    """민감정보를 제외한 사용자 응답."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: int
    username: str
    name: str | None
    email: EmailStr | None
    business_name: str | None
    business_type: str | None
    address: str | None
    address_detail: str | None
    road_address: str | None
    lat: float | None
    lng: float | None
    credits: int = Field(ge=0)
    daily_free_used: int = Field(ge=0)
    daily_free_reset_at: datetime | None
    daily_free_remaining: int = Field(ge=0)

    @field_validator("daily_free_reset_at", mode="before")
    @classmethod
    def normalize_reset_at_to_utc(cls, value: object) -> object:
        """SQLite가 timezone을 제거한 UTC 시각을 API offset으로 복원합니다."""
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value


class PreviewGenerationResult(StrictModel):
    """초기 컨테이너 연결 검증용 결과."""

    text: str


class PreviewGenerateResponse(StrictModel):
    """초기 컨테이너 연결 검증용 응답."""

    request_id: str
    status: Literal["completed"]
    result: PreviewGenerationResult


class GenerateExtra(StrictModel):
    """두 챗봇이 공유하는 선택형 추가 입력."""

    purpose: str | None = Field(default=None, max_length=200)
    price_range: str | None = Field(default=None, max_length=100)
    target_age: str | None = Field(default=None, max_length=50)
    strength: str | None = Field(default=None, max_length=200)
    clarification: str | None = Field(default=None, max_length=500)


class GenerateEstimateRequest(StrictModel):
    """Frontend가 생성 전 Estimate에 보내는 요청."""

    chatbot_type: ChatbotType
    question: str = Field(min_length=1, max_length=2_000)
    platform: Platform | None = None
    extra: GenerateExtra | None = None
    source_gen_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_platform(self) -> "GenerateEstimateRequest":
        """챗봇 종류에 따라 플랫폼 사용 여부를 검증합니다."""
        if self.chatbot_type == "basic" and self.platform is None:
            raise ValueError("Basic 요청에는 platform이 필요합니다.")
        if self.chatbot_type == "consultant" and self.platform is not None:
            raise ValueError("Consultant 요청은 platform을 사용하지 않습니다.")
        return self


class GenerateRequest(GenerateEstimateRequest):
    """실제 생성 요청. Estimate 이후 사용자가 승인한 Credit 상한을 포함합니다."""

    max_accepted_credits: int = Field(ge=0)


class GenerateEstimateResponse(StrictModel):
    """생성 전 예상 과금 정보."""

    is_free: bool
    free_remaining: int = Field(ge=0)
    estimated_credits: int = Field(ge=0)
    current_credits: int = Field(ge=0)
    credits_after: int = Field(ge=0)
    requires_confirmation: bool


class GenerationUsage(StrictModel):
    """생성 요청에 실제 적용한 사용량 정보."""

    plan: Literal["free", "paid"]
    credits_used: int = Field(ge=0)


class StoreContext(StrictModel):
    """Service가 사용자 DB에서 구성하는 가게 Context."""

    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    address: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ModelRequest(StrictModel):
    """Service가 모델 Client에 전달하는 요청."""

    chatbot_type: ChatbotType
    user_id: int = Field(gt=0)
    question: str = Field(min_length=1, max_length=2_000)
    platform: Platform | None = None
    store: StoreContext
    extra: GenerateExtra | None = None
    source_context: "ConsultantSourceContext | None" = None

    @model_validator(mode="after")
    def validate_platform(self) -> "ModelRequest":
        """챗봇 종류에 따라 플랫폼 사용 여부를 검증합니다."""
        if self.chatbot_type == "basic" and self.platform is None:
            raise ValueError("Basic 모델 요청에는 platform이 필요합니다.")
        if self.chatbot_type == "consultant" and self.platform is not None:
            raise ValueError("Consultant 모델 요청은 platform을 사용하지 않습니다.")
        return self


class ProposalError(StrictModel):
    """Basic Proposal 한 슬롯의 실패 정보."""

    field: Literal["copy", "image"]
    reason: Literal[
        "rate_limit", "content_policy", "timeout", "unknown", "parse_failed"
    ]
    message: str = Field(min_length=1)


class BasicProposal(StrictModel):
    """Basic 결과의 고정 Proposal 슬롯."""

    copy_text: str | None = Field(alias="copy", serialization_alias="copy")
    image_b64: str | None = None
    error: ProposalError | None = None

    @property
    def copy(self) -> str | None:
        """외부 계약명 copy에 대응하는 값을 반환합니다."""
        return self.copy_text

    @model_validator(mode="after")
    def validate_slot_state(self) -> "BasicProposal":
        """카피·이미지·오류 조합의 불변 조건을 검증합니다."""
        if self.error is None:
            if self.copy_text is None or not self.copy_text.strip():
                raise ValueError("성공 슬롯에는 비어 있지 않은 copy가 필요합니다.")
            return self

        if self.error.field == "copy":
            if self.copy_text is not None or self.image_b64 is not None:
                raise ValueError("카피 실패 슬롯은 copy와 image_b64가 null이어야 합니다.")
            return self

        if self.copy_text is None or not self.copy_text.strip() or self.image_b64 is not None:
            raise ValueError("이미지 실패 슬롯은 copy만 유지해야 합니다.")
        return self


class BasicModelResult(InboundModel):
    """기본 챗봇의 성공 또는 부분 성공 결과."""

    status: Literal["ok"]
    title: str = Field(min_length=1)
    proposals: list[BasicProposal] = Field(min_length=3, max_length=3)
    sources: list[str] = Field(default_factory=list)
    tokens_used: int = Field(ge=0)
    suggested_chips: list[str] = Field(default_factory=list, max_length=0)


class ConsultantAction(StrictModel):
    """컨설턴트가 제안하는 실행 항목."""

    type: Literal["menu", "promotion", "target", "other"]
    content: str = Field(min_length=1)


class ConsultantStrategy(StrictModel):
    """컨설턴트 전략 요약과 실행 항목."""

    summary: str = Field(min_length=1)
    actions: list[ConsultantAction] = Field(min_length=1, max_length=3)




class ConsultantSourceContext(StrictModel):
    """Consultant 성공 결과에서 서버가 구성하는 Basic 연계 Context."""

    generation_id: int = Field(gt=0)
    strategy: ConsultantStrategy
    reasons: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    sources: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)


class ConsultantModelResult(InboundModel):
    """컨설턴트 챗봇의 성공 결과."""

    status: Literal["ok"]
    title: str = Field(min_length=1)
    strategy: ConsultantStrategy
    reasons: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    sources: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    tokens_used: int = Field(ge=0)
    suggested_chips: list[Annotated[str, Field(min_length=1)]] = Field(
        min_length=3, max_length=3
    )


class BlockedResult(InboundModel):
    """정책 검증으로 생성이 중단된 결과."""

    status: Literal["blocked"]
    action: Literal["block", "reask", "warn"]
    reason: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ErrorResult(InboundModel):
    """모델 또는 외부 제공자 실행 실패 결과."""

    status: Literal["error"]
    reason: Literal["timeout", "rate_limit", "provider_error", "unknown"]
    message: str = Field(min_length=1)


ModelResult = BasicModelResult | ConsultantModelResult | BlockedResult | ErrorResult
PublicGenerationResult = BasicModelResult | ConsultantModelResult | BlockedResult


class _ModelResultEnvelope(BaseModel):
    """명시적 ModelResult 분기에 필요한 최상위 status만 검증합니다."""

    model_config = ConfigDict(extra="ignore")

    status: Literal["ok", "blocked", "error"]


class ModelResultAdapter:
    """status와 이미 알고 있는 chatbot_type으로 ModelResult를 명시적으로 검증합니다."""

    def validate_python(
        self, value: object, *, chatbot_type: ChatbotType
    ) -> ModelResult:
        """성공 결과는 요청 chatbot_type의 Schema 하나만 검증합니다."""
        if chatbot_type not in ("basic", "consultant"):
            raise ValueError("chatbot_type은 basic 또는 consultant여야 합니다.")

        payload = (
            value.model_dump(mode="python", by_alias=True)
            if isinstance(value, BaseModel)
            else value
        )
        status = _ModelResultEnvelope.model_validate(payload).status

        if status == "blocked":
            return BlockedResult.model_validate(payload)
        if status == "error":
            return ErrorResult.model_validate(payload)
        if chatbot_type == "basic":
            return BasicModelResult.model_validate(payload)
        return ConsultantModelResult.model_validate(payload)


MODEL_RESULT_ADAPTER = ModelResultAdapter()


class GenerationResponse(StrictModel):
    """Service가 Frontend에 반환하는 생성 작업 응답."""

    generation_id: int = Field(gt=0)
    status: GenerationStatus
    chatbot_type: ChatbotType
    result: PublicGenerationResult | None = None
    usage: GenerationUsage
