# D4 ModelResult 리뷰 후속 설계

## 목표

PR #88 리뷰에서 남은 Model→Service 입력 경계 개선을 D4 자식 브랜치에 모은다.
기존 #88·#89 브랜치와 D4 생성 오케스트레이션 동작은 변경하지 않는다.

## 변경 범위

- `backend/schemas.py`
  - Model→Service 최상위 결과 전용 `InboundModel`을 추가한다.
  - `BasicModelResult`, `ConsultantModelResult`, `BlockedResult`, `ErrorResult`가 이를 상속한다.
  - `InboundModel`은 미정의 최상위 필드를 무시하되 필드 이름만 `INFO` 로그로 남긴다.
  - 내부 분기용 `_ModelResultEnvelope`는 `InboundModel`을 상속하지 않는다. 정상 payload의 모든 필드를 미정의 필드로 중복 기록하지 않기 위해서다.
- `tests/schemas/test_consultant_result.py`
  - Basic payload 거부가 `suggested_chips=[]`가 아니라 `strategy`·`reasons` 누락 때문에 발생했음을 고정한다.
- `tests/schemas/test_model_result_extra_policy.py`
  - `ProposalError`와 `ConsultantAction`도 중첩 미정의 필드를 거부하는지 검증한다.
  - 최상위 미정의 필드가 무시되면서 필드 이름이 한 번 기록되는지 검증한다.

## 불변조건

- Public Frontend→Service 모델은 계속 `extra="forbid"`다.
- Model→Service 완화는 네 최상위 결과 모델에만 적용한다.
- `BasicProposal`, `ProposalError`, `ConsultantStrategy`, `ConsultantAction`은 계속 strict다.
- `MODEL_RESULT_ADAPTER`의 `status + chatbot_type` 명시 분기는 변경하지 않는다.
- 로그에는 미정의 필드 이름만 남기고 값은 남기지 않는다.

## 테스트 전략

1. 구현 전에 실패 테스트를 추가한다.
2. `InboundModel` 부재, ignored-key 로그 부재, 중첩 strict 누락을 각각 기대한 이유로 실패하는지 확인한다.
3. 최소 구현 후 스키마 테스트를 통과시킨다.
4. 최종 검증은 `uv run --locked --all-groups pytest`와 `uv run --locked --group dev ruff check .`을 기준으로 한다.

## 제외 범위

- D4 생성 transaction, 과금, idempotency 변경
- Actual 모델 연동
- `market_cache` 소유권 또는 bootstrap 변경
- D5 프론트엔드 구현
