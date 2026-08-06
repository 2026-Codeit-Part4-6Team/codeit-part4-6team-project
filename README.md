# Codeit Part 4 6팀 프로젝트

생성형 AI를 활용해 소상공인의 광고 콘텐츠 제작을 돕는 서비스입니다.

현재 저장소는 POC에서 검증한 사용자 흐름을 팀 프로젝트 구조로 옮기는 초기 단계입니다.

> 현재 FastAPI·Streamlit 코드와 포트 매핑은 uv, Docker 빌드, 컨테이너 통신 및 외부 접근을 확인하기 위한 임시 스켈레톤입니다. 최종 서비스 요구사항이 확정되면 관련 구현과 API 계약을 교체하거나 제거합니다.

## 빠른 실행

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
docker compose down
```

- 프론트엔드: `http://localhost:8501`
- 백엔드 헬스체크: `http://localhost:18000/health`
- 백엔드 API 문서: `http://localhost:18000/docs`

GCP에서 프론트엔드를 80번 포트로 확인하려면 서버의 `.env`에 `FRONTEND_PORT=80`을 지정합니다. 현재 `/generate`는 프론트엔드와 백엔드 연결을 확인하기 위한 목 응답이며 최종 API 계약이 아닙니다.

## Python 의존성

Docker 실행만 할 경우 로컬에 uv를 설치할 필요가 없습니다. Dockerfile이 `uv.lock`을 기준으로 필요한 패키지를 설치합니다.

로컬에서 코드와 테스트를 실행할 경우 다음 명령을 사용합니다.

```bash
uv sync --locked --all-groups
uv run --locked --all-groups pytest
uv run --locked --group dev ruff check .
```

의존성은 `uv add --group backend 패키지명`처럼 해당 그룹을 지정해 추가합니다. `pyproject.toml`과 `uv.lock`을 원본으로 관리하며 `uv.lock`과 `requirements.txt`는 직접 수정하지 않습니다.

의존성을 변경한 경우 `pyproject.toml`, `uv.lock`, `requirements.txt`를 함께 반영합니다.

```bash
uv export --locked --no-default-groups \
  --group backend --group frontend \
  --format requirements.txt --output-file requirements.txt
```

서비스별 실행환경과 포트는 다음 문서를 확인해주세요.

- [백엔드 안내](backend/README.md)
- [프론트엔드 안내](frontend/README.md)

## CI/CD

`main` 대상 PR에서는 Python 테스트와 Docker Compose 스모크 테스트를 자동 수행합니다.
CI를 통과해 `main`에 병합된 뒤에는 수동 배포 워크플로를 실행합니다. 배포 워크플로는
Artifact Registry에 커밋 SHA 기반 이미지를 저장한 뒤 GCP VM의 애플리케이션 컨테이너만
교체합니다. JupyterHub와 모델 실험 환경은 배포 대상에 포함하지 않습니다.

- [CI/CD 설정 및 운영 안내](.github/workflows/README.md)
