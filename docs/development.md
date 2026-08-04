# 개발환경 안내

## 기본 환경

- Python: 3.11
- 패키지 관리: uv
- 백엔드: FastAPI
- 프론트엔드: Streamlit
- 컨테이너 실행: Docker Compose

## 의존성 관리

`pyproject.toml`과 `uv.lock`을 의존성의 원본으로 사용합니다. `uv.lock`은 직접 수정하지 않습니다.

```bash
# 로컬 개발환경 구성
uv sync --group backend --group frontend --group dev

# 백엔드 의존성 추가
uv add --group backend 패키지명

# 프론트엔드 의존성 추가
uv add --group frontend 패키지명

# 개발 도구 추가
uv add --group dev 패키지명
```

호환용 `requirements.txt`가 필요한 경우 아래 명령으로 생성하며 직접 수정하지 않습니다.

```bash
uv export --locked --no-default-groups \
  --group backend --group frontend \
  --format requirements.txt --output-file requirements.txt
```

의존성을 변경한 PR에는 `pyproject.toml`과 `uv.lock`을 함께 포함합니다.

## 로컬 실행

```bash
cp .env.example .env
docker compose up --build
```

종료 및 로그 확인 명령은 다음과 같습니다.

```bash
docker compose down
docker compose logs -f
```

## 포트 정책

| 용도 | 호스트 포트 | 컨테이너 포트 | 비고 |
| --- | ---: | ---: | --- |
| Streamlit | 8501 | 8501 | 사용자 접근용 |
| FastAPI | 18000 | 8000 | 초기 검증용 |
| JupyterHub | 8000 | - | VM에 별도 구성 |

서비스 내부에서 프론트엔드는 `http://backend:8000`으로 백엔드에 접근합니다. 운영 배포에서 Nginx와 HTTPS를 구성한 이후에는 FastAPI의 직접 외부 노출을 제거할 예정입니다.

## 검증

```bash
uv run --group backend --group dev pytest
uv run --group dev ruff check .
docker compose config
curl http://localhost:18000/health
```
