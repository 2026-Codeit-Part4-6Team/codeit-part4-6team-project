# Service SDP Alignment Design

## Goal

Rewrite `docs/sdp_service.md` from `origin/main` so it describes the current service architecture, completed work, remaining D7-D10 gates, and ownership boundaries according to the latest `docs/decisions.md`.

## Source Priority

1. `docs/decisions.md` is the policy and decision SSOT.
2. D1-D10 implementation contracts define API, DTO, ownership, and completion boundaries.
3. D1-D10 milestone plans define intended sequencing and DoD.
4. The repository code and PR state provide implementation evidence.

If sources conflict, the SDP will record the latest decision and explicitly mark stale source text for follow-up rather than silently choosing an old plan.

## Document Shape

The revised SDP will retain the useful existing sections but change their meaning from a pre-development proposal to a status-aware execution document:

- Project overview and service responsibility
- Scope split by D1-D10 and ownership
- Completed, in-progress, gated, and deferred status
- Current React/FastAPI/SQLite/Docker architecture
- Contract boundaries between Service, Model, PM validation, Cache, and Infrastructure
- Updated D1-D10 schedule and completion criteria
- Verification evidence and known gaps
- Risks, decisions, and next actions

## Status Rules

- `완료`: implementation and relevant verification evidence exist.
- `진행/연동 대기`: implementation exists but an external dependency or review remains.
- `Gate`: an explicit contract, catalog, provider, or ownership decision is required before completion.
- `후속`: intentionally outside the current milestone and not required for the current completion claim.

The document will not claim D7 actual Provider integration, D8 publish, D9 payment/history, or D10 full E2E/deployment completion when those gates are not closed.

## Key Corrections

- Replace Streamlit as the default frontend plan with the current React D5/D6 path, while retaining Streamlit only as historical POC context if useful.
- Replace Basic/Consultant cost reversal with Basic 50 and Consultant 10.
- Replace stale `request_id` language with `Idempotency-Key`.
- Replace the old three-platform assumption with Instagram and banner; blog is excluded.
- Describe Consultant results as nested strategy/actions/reasons/sources, not flattened Basic proposals.
- Describe `platform=null` for Consultant and the shared five-field `GenerateExtra` contract.
- Clarify that StoreContext is assembled by Backend from authenticated user/store data.
- Clarify that Provider/model selection is not finalized and must remain configuration-driven.
- Separate local Docker health verification from production deployment; GCP/CD remains Infrastructure-owned and manually gated.
- Make D4/D7/D8/D9/D10 dependencies explicit so the next work is not presented as completed.

## Out of Scope

- Modifying D1-D10 implementation contracts in this pass.
- Modifying application code.
- Resolving open model or payment Gates by assumption.
- Rewriting historical decisions.
- Creating or merging a PR from this documentation branch.
