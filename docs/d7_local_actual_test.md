# D7 실제 모델 로컬 통합 테스트

테스트 브랜치: `test/d7-actual-model-e2e`

이 브랜치는 로컬 Docker Compose 환경에서 다음 경로를 검증하기 위한 통합 전용 브랜치다.

```text
Docker Compose
→ FastAPI /generate
→ Service Generation orchestration
→ ActualChatbotClient
→ models/basic/main.py::run() 또는 models/consult/main.py::run()
→ ModelResult dict
→ Service schema 검증 / DB 저장
```

GCP 배포는 이 테스트 범위에 포함하지 않는다.

## 1. `.env` 준비

프로젝트 표준 `.env`를 사용한다. 처음이면:

```bash
cp .env.example .env
```

Actual 모델 통합 테스트에는 최소 아래 값을 설정한다.

```dotenv
CHATBOT_MODE=actual
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
```

`OPENAI_API_KEY`는 실제 Basic / Consultant LLM 호출에 필수다.

실제 외부 상권/트렌드 데이터까지 확인하려면 아래 키도 설정한다.

```dotenv
MARKET_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_AD_API_KEY=
NAVER_AD_SECRET_KEY=
NAVER_AD_CUSTOMER_ID=
```

회원가입의 실제 NAVER Geocoding까지 함께 검증할 경우에는 아래 값도 설정한다.

```dotenv
NAVER_MAPS_API_KEY_ID=
NAVER_MAPS_API_KEY=
```

## 2. Docker Compose로 실제 모델 실행

Backend image는 `backend`, `model-consult`, `basic` dependency group을 모두 설치하고 `models/`를 이미지에 포함한다.

빌드 및 실행:

```bash
docker compose up --build
```

Backend 로그:

```bash
docker compose logs -f backend
```

Health 확인:

```bash
curl http://127.0.0.1:18000/health
```

`.env`의 `CHATBOT_MODE=actual`이면 Backend startup 시 Basic / Consultant의 `main.py::run()` 진입점을 로드한다. 진입점 또는 모델 dependency가 없으면 Mock으로 조용히 fallback하지 않고 startup이 실패한다.

## 3. Service↔Model 경계만 빠르게 확인하는 smoke script

Docker 전체 UI 흐름과 별개로 `/generate`와 실제 모델 경계만 빠르게 확인하려면:

```bash
uv sync --locked --group backend --group dev --group model-consult --group basic
uv run --env-file .env python scripts/local_actual_smoke.py --chatbot both
```

Basic만:

```bash
uv run --env-file .env python scripts/local_actual_smoke.py --chatbot basic
```

Consultant만:

```bash
uv run --env-file .env python scripts/local_actual_smoke.py --chatbot consultant
```

smoke script는 임시 SQLite DB와 테스트 사용자를 준비하고 실제 `/generate` endpoint를 호출한다. 회원가입/Geocoding을 분리한 상태에서 Service↔Model 호출 경계를 확인하기 위한 보조 테스트다.

- exit `0`: Service→실제 모델→Service 계약 경로 관통
- exit `1`: `/generate` non-200 또는 예상하지 않은 generation 상태
- exit `2`: 필수 환경변수 누락

## 4. 확인 범위

- Basic `run(request: dict) -> dict`
- Consultant `run(request: dict) -> dict`
- Service `ModelRequest` dict 전달
- `asyncio.to_thread()` 기반 동기 모델 호출
- ModelResult schema 검증
- Generation 저장 / 사용량 정산
- timeout / provider 오류가 Service 실패 경로로 들어오는지
- Docker image에 Actual 모델 코드/의존성이 실제 포함되는지

실제 모델 품질과 GCP 배포는 이 브랜치의 완료 조건이 아니다.
