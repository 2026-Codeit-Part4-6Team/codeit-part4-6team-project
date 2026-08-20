# D7 실제 모델 로컬 통합 테스트

테스트 브랜치: `test/d7-actual-model-e2e`

이 브랜치는 다음 조합을 로컬에서 검증하기 위한 통합 전용 브랜치다.

```text
FastAPI /generate
→ Service Generation orchestration
→ ActualChatbotClient
→ models/basic/main.py::run() 또는 models/consult/main.py::run()
→ ModelResult dict
→ Service schema 검증 / DB 저장
```

GCP/Docker 배포는 이 테스트 범위에 포함하지 않는다.

## 1. Python / dependency 준비

프로젝트는 Python 3.11을 사용한다.

```bash
uv sync --locked --group backend --group dev --group model-consult --group basic
```

Basic 모델은 현재 import 단계에서 `torch`, `transformers`를 사용하므로 `basic` group도 필요하다.

## 2. 환경변수 준비

```bash
cp .env.actual.example .env.actual
```

`.env.actual`에서 최소 아래 값만 실제 값으로 채운다.

```dotenv
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_API_KEY`는 필수다. `OPENAI_MODEL`은 이 예제에서 명시적으로 채워 둔다.

아래 키들은 **실제 외부 상권/트렌드 데이터까지 확인할 때만 필요**하다.

```dotenv
MARKET_API_KEY=
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NAVER_AD_API_KEY=
NAVER_AD_SECRET_KEY=
NAVER_AD_CUSTOMER_ID=
```

키가 없으면 해당 상권/트렌드 조회는 `None`으로 폴백하도록 현재 모델 코드가 구현되어 있어, Service↔Model 호출 경계 smoke 자체는 진행할 수 있다.

`NAVER_MAPS_API_KEY_ID`, `NAVER_MAPS_API_KEY`는 이 smoke script에서는 필요하지 않다. 테스트 사용자를 DB에 직접 준비하므로 회원가입 Geocoding을 거치지 않는다. 일반 `/auth/register`까지 수동 검증하려면 해당 키 또는 development fallback 설정이 필요하다.

## 3. 실제 호출 smoke

Basic만:

```bash
uv run --env-file .env.actual python scripts/local_actual_smoke.py --chatbot basic
```

Consultant만:

```bash
uv run --env-file .env.actual python scripts/local_actual_smoke.py --chatbot consultant
```

둘 다:

```bash
uv run --env-file .env.actual python scripts/local_actual_smoke.py --chatbot both
```

스크립트는 임시 SQLite DB를 만들고 테스트 사용자를 준비한 뒤 실제 `/generate` endpoint를 호출한다. 따라서 회원가입/UI와 분리해서 D7의 Service↔Model 통합 경계를 확인할 수 있다.

- exit `0`: 요청이 Service→실제 모델→Service까지 계약에 맞게 관통
- exit `1`: 실제 `/generate`가 non-200 또는 예상하지 않은 generation 상태 반환
- exit `2`: 필수 환경변수 누락

정책 검증으로 `BlockedResult`가 반환되어 generation 상태가 `failed`인 경우에도 HTTP 200 + 계약에 맞는 결과라면 통합 경계 자체는 성공으로 본다.

## 4. 이 브랜치에서 확인할 것

- Basic 실제 `run(request: dict) -> dict`
- Consultant 실제 `run(request: dict) -> dict`
- Service `ModelRequest` dict 전달
- `asyncio.to_thread()` 기반 동기 모델 호출
- ModelResult schema 검증
- Generation 저장 / 무료 사용량 정산
- timeout / provider 오류가 Service 실패 경로로 들어오는지

실제 모델 품질, GCP 배포, Docker actual-model image 구성은 이 브랜치의 완료 조건이 아니다.
