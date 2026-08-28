# 컨설턴트 검증 3종 연결 결정 기록

- 2026-08-27. 세 노드는 이미 그래프에 존재하지만 실구현 판정을 상태·응답에 반영하지 않아 DoD가 미완료다.
- 2026-08-27. `validation/`은 PM 소유이므로 import해서 사용만 하고 내부는 수정하지 않는다.
- 2026-08-27. D-158에 따라 컨설턴트에는 법률 규제 검증 노드를 연결하지 않는다.
- 2026-08-27. 출력 검증은 D-145·D-154에 따라 summary·actions·reasons를 합친 문자열 1개가 아니라 각 사용자 노출 조각별로 수행한다.
- 2026-08-27. self_check 재시도 카운터는 기존 strategy 내부 `retry_count`와 분리한다.
- 2026-08-27. 이번 구현은 현재 체크아웃에서 `main` 기준 `codex/model-consult-validation-integration` 브랜치로 진행한다.
- 2026-08-27. self_check에는 그래프 최상위 `sources`를 검증 context에 합쳐 전달한다. 그렇지 않으면 정상 출처가 있어도 항상 `출처 미표기` warn이 발생한다.
- 2026-08-27. self_check 재생성 전의 actions 복구 이력은 OR 누적으로 보존한다. 두 번째 strategy 실행 결과의 False가 첫 실행 이력을 덮지 않게 한다.
- 2026-08-27. 최종 검증은 컨설턴트 387개 테스트와 저장소 전체 978개 테스트 통과, `ruff check models/consult` 통과다.
- 2026-08-27. PR 전 재검토에서 `validation_contract.md`와 맞지 않던 출력 검증 기록 형식·`sensitive_leak` 사유·self-check `reject` action을 바로잡았다.
