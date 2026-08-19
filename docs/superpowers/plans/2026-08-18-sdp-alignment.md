# Service SDP Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `docs/sdp_service.md` from a stale pre-development proposal into a current, decision-led D1-D10 execution/status plan.

**Architecture:** Keep `docs/decisions.md` as the policy SSOT and treat D1-D10 implementation contracts as the API/ownership SSOT. Update only the service SDP in this branch; preserve historical decision logs and implementation contracts. Use explicit status labels to distinguish completed implementation, integration wait, gates, and deferred work.

**Tech Stack:** Markdown, Git, repository documents, D1-D10 implementation contracts, D1-D10 milestone plans.

## Global Constraints

- Work from `origin/main` on `docs/sdp-alignment`.
- Do not modify application code.
- Do not rewrite `docs/decisions.md` history.
- Do not silently resolve contradictions; record the latest decision and name stale source text when needed.
- Do not claim D7 actual Provider integration, D8 publish, D9 payment/history, or D10 full E2E/deployment completion without evidence.

---

### Task 1: Establish the Current Baseline

**Files:**
- Read: `docs/decisions.md`
- Read: `docs/sdp_service.md`
- Read: D1-D10 implementation contracts and milestone plans under the personal document source set

- [ ] Identify the latest decision IDs affecting service scope, costs, API contracts, model boundaries, validation, deployment, and D7-D10 gates.
- [ ] Record the actual evidence available for D1-D6: code locations, tests, PRs, and Docker checks.
- [ ] Record unsupported completion claims that must become `Gate`, `진행/연동 대기`, or `후속`.

### Task 2: Rewrite Scope and Ownership

**File:** `docs/sdp_service.md`

- [ ] Replace the Streamlit-first frontend assumption with the current React D5/D6 path and preserve Streamlit only as historical POC context where useful.
- [ ] Define Service ownership: React frontend, FastAPI API, SQLAlchemy/SQLite service tables, usage/credit orchestration, API/DTO boundaries, and Docker integration.
- [ ] Define non-Service ownership: Basic/Consultant model internals, validation function ownership, cache DDL/data ownership, and infrastructure deployment ownership.
- [ ] Correct policy values to Basic 50, Consultant 10, and shared daily free usage 10.
- [ ] Correct platform scope to Instagram and banner; exclude blog.

### Task 3: Rewrite D1-D6 Status and Architecture

**File:** `docs/sdp_service.md`

- [ ] Describe D1 service foundation and its four-table boundary.
- [ ] Describe D2 username/session/bcrypt/geocoding behavior and unresolved Provider transport Gate if still open.
- [ ] Describe D3 usage/credit reservation, Estimate, rollback, and 402 contract.
- [ ] Describe D4 idempotency, request hash, transaction boundaries, Mock client, source generation, compensation, and review follow-ups.
- [ ] Describe D5 React auth/Dashboard/Sidebar status separately from D6 React input/results status.
- [ ] Record current D5/D6 implementation evidence without claiming actual Provider integration.

### Task 4: Rewrite D7-D10 Plan and Gates

**File:** `docs/sdp_service.md`

- [ ] Define D7 as actual Basic/Consultant entrypoint wiring, Provider configuration, response assembly, explicit `chatbot_type` dispatch, and integration verification.
- [ ] Define D8 as paid consent, synchronous waiting/error states, Basic three-slot approval, publish CAS, and image validation/storage rules.
- [ ] Define D9 as summary/history/payment features with package catalog, payment status, duplicate payment, and catalog SSOT Gates.
- [ ] Define D10 as full integration stabilization and E2E; separate local Compose verification from manually gated production deployment.
- [ ] Mark chat log persistence, chat rooms, Provider selection details, and other unresolved product choices as deferred or Gate items.

### Task 5: Update Schedule, DoD, and Risk Register

**File:** `docs/sdp_service.md`

- [ ] Replace stale August 10-24 “planned” claims with status-aware milestone entries.
- [ ] Add evidence-based DoD for completed D1-D6 work.
- [ ] Add explicit prerequisites for D7-D10 completion.
- [ ] Update risks to include contract drift, stale stacked branches, actual ModelResult assembly, payment Gates, and production environment validation.
- [ ] Remove outdated API counts, Streamlit-only file lists, obsolete `request_id`, and reversed credit values.

### Task 6: Document Self-Review and Verification

**Files:**
- Review: `docs/sdp_service.md`
- Review: `docs/decisions.md`
- Review: all changed files in this branch

- [ ] Search the revised SDP for stale terms: `Streamlit 기본안`, `Basic 10`, `Consultant 50`, `request_id`, `blog`, and claims that D7-D10 are complete.
- [ ] Check every D1-D10 section has an owner, status, dependency, and completion boundary.
- [ ] Check all referenced paths exist in `origin/main` or are explicitly labeled as planned/contract paths.
- [ ] Run Markdown link/path checks available in the repository.
- [ ] Run `git diff --check`.
- [ ] Commit the SDP revision separately from the design and plan documents.
