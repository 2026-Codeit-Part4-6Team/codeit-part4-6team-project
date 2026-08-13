# D4 Generation Orchestration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the D4 `/generate` orchestration contract from authenticated request through idempotency, reservation, model execution, persistence, replay, and compensation.

**Architecture:** Keep HTTP concerns in `generate_router.py`, transaction/state logic in `generation_service.py`, and reuse D3 credit/usage reservation primitives. Assemble a server-owned `ModelRequest`, commit `generating` before the model call, and perform success/failure transaction 2 with settle/compensation only after the corresponding DB commit.

**Tech Stack:** Python 3.11 contract, FastAPI, Pydantic v2, SQLAlchemy 2, SQLite, pytest, Ruff.

## Global Constraints

- Basic credit cost 50; Consultant credit cost 10 via existing settings/decisions ownership.
- `MODEL_REQUEST_TIMEOUT_SECONDS >= 60`.
- `Idempotency-Key` is a required UUID.
- Request hash is SHA-256 of `GenerateRequest.model_dump(mode="json", exclude_none=False)` serialized with sorted JSON keys; `max_accepted_credits` is included.
- `source_context` is server-only and never comes from the public body.
- Do not hold a DB write transaction during the model network call.
- `ErrorResult` is stored only as safe replay metadata and never returned in public `GenerationResponse.result`.
- Business compensation applies only after transaction 1 has committed.

---

### Task 1: Complete D4 model request schema

**Files:**
- Modify: `backend/schemas.py`
- Test: `tests/schemas/test_model_request.py`

**Interfaces:**
- Produces: `ConsultantSourceContext`; `ModelRequest.source_context: ConsultantSourceContext | None`.

- [x] Add failing schema tests proving a Basic ModelRequest accepts a server-built consultant source context and a public `GenerateRequest` rejects a `source_context` field.
- [x] Run `python3 -m pytest tests/schemas/test_model_request.py tests/schemas/test_d3_generation_contract.py -q` and verify the new source-context test fails before implementation.
- [x] Add `ConsultantSourceContext(generation_id, strategy, reasons, sources)` and nullable `source_context` to `ModelRequest` only.
- [x] Re-run the schema tests and verify pass.
- [x] Commit `feat: add consultant source context contract`.

### Task 2: Add generation validation, hashing, source resolution, and replay primitives

**Files:**
- Modify: `backend/services/generation_service.py`
- Test: `tests/services/test_generation.py`

**Interfaces:**
- Produces: `IdempotencyConflict`, `SourceGenerationNotFound`, `SourceGenerationConflict`, `GenerationDataInvariantError`, `ModelExecutionError`.
- Produces helpers for request hash, Store/ModelRequest assembly, stored ModelResult restore, and replay response.

- [x] Replace Preview-only service tests with focused tests for deterministic request hash, Store validation, source ownership/type/status/schema validation, and same-key hash conflict without DB mutation.
- [x] Run those tests and verify RED.
- [x] Implement canonical request hashing, Store assembly from User fields, source_gen lookup/validation, and result restore via `MODEL_RESULT_ADAPTER`.
- [x] Implement response construction for pending/generating/done/failed-blocked/published existing rows; failed ErrorResult raises `ModelExecutionError` with stored reason.
- [x] Re-run focused tests and verify GREEN.
- [x] Commit `feat: add generation request validation and replay`.

### Task 3: Implement transaction 1 and transaction 2 orchestration

**Files:**
- Modify: `backend/services/generation_service.py`
- Test: `tests/services/test_generation.py`

**Interfaces:**
- Consumes: `reserve_generation_usage`, `settle_generation_usage`, rollback primitives, `ChatbotClient.generate`.
- Produces: async `generate(db, user, request, idempotency_key, chatbot_client, *, now, free_limit, model_timeout_seconds) -> GenerationResponse`.

- [x] Add RED tests for free Basic success, paid Consultant success, billing confirmation 409-domain exception before insert, insufficient credits before insert, pending→generating→done, Basic image_b64 stripped from storage, blocked compensation, ErrorResult compensation, client exception compensation, and no double model call/charge on same-key replay.
- [x] Implement transaction 1: reserve, pending insert, flush, generating, commit. Catch IntegrityError by rollback and replay/conflict re-query only; never business-compensate pre-commit.
- [x] Call the model outside the committed write transaction with `asyncio.wait_for`, then validate via `MODEL_RESULT_ADAPTER` using request chatbot_type.
- [x] Implement transaction 2 success: re-read id+user, require generating, safe serialize, title/tokens/status done, commit, then settle reservation.
- [x] Implement transaction 2 blocked/error: failed row, apply compensation once, zero charged/tokens, safe result_json, commit, finalize rollback; on compensation commit failure reset marker and raise internal `ModelExecutionError("unknown")`.
- [x] Re-run service tests and verify GREEN.
- [x] Commit `feat: orchestrate generation reservations and model results`.

### Task 4: Add stale same-key generating recovery

**Files:**
- Modify: `backend/services/generation_service.py`
- Test: `tests/services/test_generation.py`

**Interfaces:**
- Produces: `recover_stale_generating(db, generation, user, *, now, model_timeout_seconds) -> bool`.

- [x] Add RED tests that pre-threshold generating returns current state without charge/model call; stale paid refunds once and marks failed; stale free decrements only in the same reset period; repeated retry never refunds twice.
- [x] Implement stale check using `as_utc(created_at)` and `2 * model_timeout_seconds`.
- [x] For stale paid, add stored credits once. For stale free, compare current reset period with `next_seoul_midnight_utc(generation.created_at)` before decrement.
- [x] Store safe internal ErrorResult `stale_generation_recovered`, zero usage/tokens, set failed, commit; rollback on commit failure.
- [x] Re-run service tests and verify GREEN.
- [x] Commit `feat: recover stale idempotent generations`.

### Task 5: Wire one Mock ChatbotClient into the app

**Files:**
- Modify: `backend/clients/chatbot_client.py`
- Modify: `backend/main.py`
- Test: `tests/clients/test_mock_chatbot.py`
- Test: `tests/api/test_generation.py`

**Interfaces:**
- Produces: a single routing `MockChatbotClient` that delegates by `ModelRequest.chatbot_type`.
- Produces: `app.state.chatbot_client` created once in `create_app()`.

- [x] Add RED tests that one routing client supports both chatbot types and `create_app()` owns a persistent `app.state.chatbot_client`.
- [x] Implement the routing Mock client by composing existing Basic/Consultant mocks without DB knowledge.
- [x] Assign it once during app creation; router must not instantiate clients.
- [x] Re-run client/app tests and verify GREEN.
- [x] Commit `feat: wire mock chatbot client for generation`.

### Task 6: Replace Preview `/generate` with the real D4 HTTP endpoint

**Files:**
- Modify: `backend/routers/generate_router.py`
- Test: `tests/api/test_generation.py`

**Interfaces:**
- Consumes: `GenerateRequest`, required `Idempotency-Key`, authenticated `User`, DB dependency, `app.state.chatbot_client`, async generation service.
- Produces: `POST /generate -> GenerationResponse` and contract HTTP mappings.

- [x] Rewrite API tests to authenticate a user in the isolated test DB and exercise: missing/invalid key 422, success 200, same-key same-body replay, different-body 409, insufficient 402, billing confirmation 409, source 404/409, technical 429/500/502/504 mapping, and OpenAPI request schema == `GenerateRequest`.
- [x] Implement async router endpoint with `Header(..., alias="Idempotency-Key")`, DB/current-user dependencies and injected app client.
- [x] Map only the contract domain exceptions; keep policy blocked as HTTP 200 response.
- [x] Remove or move the Preview `/generate`; do not leave duplicate path ownership.
- [x] Re-run API tests and verify GREEN.
- [x] Commit `feat: expose d4 generation endpoint`.

### Task 7: D4 completion cleanup: test DB isolation, timezone/WAL, ERD truth

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/db/test_database.py`
- Modify: `backend/database.py`
- Modify if source exists: ERD source under `docs/`
- Test: `tests/api/*`, `tests/db/test_database.py`, `tests/services/test_generation.py`

**Interfaces:**
- Test global engine defaults to in-memory DB because `DATABASE_URL` is set before backend imports.
- API fixture overrides `get_db` with tmp_path DB Session.
- File SQLite connection uses WAL; memory SQLite does not require WAL.

- [x] Move test `DATABASE_URL=sqlite:///:memory:` setup before any backend import and override `get_db` per API test using a tmp_path engine/session; add regression assertion that settings never points at `data/app.db`.
- [x] Add DB tests for file SQLite `PRAGMA journal_mode=WAL` and memory SQLite creation.
- [x] Update `create_database_engine()` to keep `foreign_keys=ON` and set WAL only for file SQLite.
- [x] Confirm generation stale comparisons use `as_utc()` and no naive/aware direct comparison remains.
- [x] Inspect ERD assets. If an editable source exists, update it and regenerate artifact; if only PNG exists, do not fabricate a source and record the limitation in D4 notes while keeping ORM/tests as executable truth.
- [x] Re-run DB/API/service tests and verify GREEN.
- [x] Commit `chore: complete d4 database and test isolation cleanup`.

### Task 8: Final verification

**Files:**
- Review all D4 changes.

- [ ] Run `uv sync --locked --all-groups` in a network-capable Python 3.11 environment.
- [ ] Run `uv run --locked --all-groups pytest --basetemp .pytest_tmp`.
- [ ] Run `uv run --locked --group dev ruff check .`.
- [x] Run `git diff --check` and `git status --short`.
- [x] Compare implementation against every D4-B and D4-C contract bullet and record any external Gate that cannot be closed locally (notably Consultant market_cache collaboration / ERD source availability).

**Verification note (assistant sandbox, 2026-08-13):**
- Exact `uv` Python 3.11 verification is blocked because the sandbox cannot resolve GitHub to download uv's managed CPython 3.11.14; the three `uv --locked` commands remain unchecked for local/CI verification.
- Service-owned `tests/` pass under the available system Python with a temporary, non-repo bcrypt import shim; this is supplementary evidence, not a replacement for locked CI.
- Consultant `market_cache` ownership remains an external collaboration Gate: Service `create_tables()` still owns only the four service tables, while the current Consultant/cache code does not expose the shared-DB bootstrap callable required by the D4 contract. Service code does not take ownership of that DDL.
- The repository had only `docs/images/erd_sdp_service.png` and no editable ERD source. The image artifact was regenerated manually from the current ORM; no new ERD source was fabricated.
