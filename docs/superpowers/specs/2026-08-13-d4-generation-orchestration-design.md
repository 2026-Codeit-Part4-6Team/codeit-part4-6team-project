# D4 Generation Orchestration Design

## Source of truth

`서비스 구현 계약서(2).zip`의 `D4 생성 오케스트레이션 파일별 구현 계약서 — PR #69 후속 작업 범위 반영본`과 FINAL PR69 D4 통합본을 따른다. D4-A의 ModelResult top-level extra ignore와 explicit chatbot_type adapter 분기는 현재 기준선에 이미 반영되어 있다.

## Goal

`POST /generate` 한 요청이 인증 사용자, idempotency, 무료/Credit reservation, Generation 상태, Mock Model 호출, 저장, settle/compensation을 끝까지 관통한다. 같은 key 재시도는 모델 재호출/재과금을 하지 않으며 stale generating을 안전하게 복구한다.

## Architecture

`generate_router`는 HTTP/auth/header/error mapping만 담당하고, `generation_service`가 transaction 0/1/2와 replay를 조율한다. `credit_service`의 reservation primitives는 그대로 재사용하고, 모델 Client는 `app.state.chatbot_client`에서 1회 주입한다. DB write transaction은 모델 호출 동안 열어두지 않는다.

## Data flow

1. Transaction 0: UUID/header, request hash, existing idempotency row, Store/source_gen validation, ModelRequest assembly.
2. Transaction 1: free-first reservation, Generation pending insert, unique race check, generating 전이, commit.
3. Model call: async Mock client, configured timeout, ModelResult adapter validation.
4. Transaction 2: success -> done + settle; blocked/error -> failed + exactly-once compensation; commit failure leaves durable generating for stale recovery.
5. Same-key retry: hash mismatch 409; pending/generating/done/failed/published replay; stale generating is recovered without model recall.

## D4 completion cleanup

- Test DB must not touch `./data/app.db`.
- UTC storage/SQLite naive UTC normalization must be consistent through `as_utc()`.
- File SQLite WAL ownership belongs to `create_database_engine`; memory SQLite does not force WAL.
- Preview `/generate` no longer owns the real path.
- ERD source/artifact is updated if an editable source exists; if only PNG exists, document the code/schema truth and avoid fabricating an image source.

## Non-goals

- Actual model adapter/wiring beyond the D4 Mock client.
- D5 history/publish behavior beyond replaying an already-published row without generating or charging.
- Background stale sweeper; same-key retry recovery only.
