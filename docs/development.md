# 개발환경 및 의존성 관리

## 기본 환경

- Python: 3.11
- 패키지 관리: uv 0.11.32 이상
- 백엔드: FastAPI
- 프론트엔드: Streamlit
- 컨테이너 실행: Docker Compose

## uv 설계 원칙

Python 의존성은 저장소 루트에서 하나의 uv 프로젝트로 관리합니다.

- `pyproject.toml`: 사람이 수정하는 직접 의존성과 프로젝트 설정
- `uv.lock`: uv가 생성하는 전체 의존성 잠금 파일
- `requirements.txt`: uv를 사용하기 어려운 환경을 위한 파생 산출물
- `.python-version`: 로컬에서 사용할 Python 3.11 기준

`pyproject.toml`과 `uv.lock`을 의존성의 원본으로 사용합니다. `uv.lock`과 `requirements.txt`는 직접 수정하지 않습니다.

현재는 uv workspace를 사용하지 않습니다. 백엔드와 Streamlit이 하나의 배포 저장소에서 함께 변경되고 공통 lock이 필요하기 때문입니다. 서비스가 독립 배포 단위로 분리될 때 workspace 또는 저장소 분리를 다시 검토합니다.

## 의존성 그룹

| 그룹 | 용도 | 예시 |
| --- | --- | --- |
| `backend` | FastAPI 런타임 | FastAPI, Uvicorn |
| `frontend` | Streamlit 런타임 | Streamlit, HTTP 클라이언트 |
| `dev` | 로컬 검증 도구 | pytest, Ruff |

모델, Triton, Notebook 의존성은 담당 범위가 확정된 뒤 별도 그룹으로 추가합니다. 대용량 모델 패키지를 기본 백엔드 이미지에 자동으로 포함하지 않습니다.

## 로컬 환경 구성

```bash
# 전체 개발환경 구성
uv sync --group backend --group frontend --group dev

# 백엔드 의존성 추가
uv add --group backend 패키지명

# 프론트엔드 의존성 추가
uv add --group frontend 패키지명

# 개발 도구 추가
uv add --group dev 패키지명
```

의존성 변경이 없는 일반 실행과 CI에서는 lock 변경을 허용하지 않습니다.

```bash
uv sync --locked --group backend --group frontend --group dev
```

의존성을 추가하거나 제거한 PR에는 `pyproject.toml`, `uv.lock`, `requirements.txt`를 함께 포함합니다.

## requirements.txt 생성

호환용 `requirements.txt`가 필요한 경우 아래 명령으로 생성하며 직접 수정하지 않습니다.

```bash
uv export --locked --no-default-groups \
  --group backend --group frontend \
  --format requirements.txt --output-file requirements.txt
```

향후 CI에서 위 명령을 다시 실행한 뒤 Git 차이가 없는지 검사합니다.

## Docker 설치 정책

- Dockerfile은 `python:3.11-slim`을 런타임 기반 이미지로 사용합니다.
- uv 실행 파일은 버전을 고정한 공식 이미지에서 복사합니다.
- 의존성 파일을 애플리케이션 코드보다 먼저 복사해 Docker 레이어 캐시를 활용합니다.
- 백엔드와 프론트엔드는 필요한 dependency group만 설치합니다.
- `.env`와 API 키는 이미지에 포함하지 않습니다.

```text
backend image  = Python 3.11 + backend group
frontend image = Python 3.11 + frontend group
```

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
