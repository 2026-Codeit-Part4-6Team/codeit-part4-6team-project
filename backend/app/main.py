from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Codeit Part 4 Team 6 API")


class GenerateRequest(BaseModel):
    """광고 콘텐츠 생성 요청."""

    prompt: str


@app.get("/health")
def health() -> dict[str, str]:
    """서비스 상태를 반환합니다."""
    return {"status": "ok"}


@app.post("/generate")
def generate(request: GenerateRequest) -> dict[str, str]:
    """초기 연동 검증을 위한 목 생성 결과를 반환합니다."""
    return {"result": f"광고 콘텐츠 생성 요청을 확인했습니다: {request.prompt}"}
