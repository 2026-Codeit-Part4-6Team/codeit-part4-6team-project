from typing import Literal

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """광고 콘텐츠 생성 요청."""

    prompt: str = Field(min_length=1, max_length=2_000)


class GenerationResult(BaseModel):
    """광고 콘텐츠 생성 결과."""

    text: str


class GenerateResponse(BaseModel):
    """광고 콘텐츠 생성 응답."""

    request_id: str
    status: Literal["completed"]
    result: GenerationResult
