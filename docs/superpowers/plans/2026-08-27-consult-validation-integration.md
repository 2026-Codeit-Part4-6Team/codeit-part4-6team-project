# Consultant Validation Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 컨설턴트 그래프에 이미 배치된 보안1·보안2·self_check 노드가 PM 검증 함수의 판정을 실제 응답과 라우팅에 반영하도록 완성한다.

**Architecture:** `validation/` 함수는 수정하지 않고 컨설턴트 노드가 판정 dict를 상태 변화로 변환한다. 입력 warn/block과 출력 block은 즉시 종료하고, 출력 warn은 각 응답 필드에 마스킹을 적용하며, self_check reject는 전략 노드만 최대 1회 재실행한다.

**Tech Stack:** Python, LangGraph, pytest, unittest.mock, Ruff.

**Spec:** `docs/validation_contract.md` §6·§8, `docs/sdp_consult.md` 검증 함수 3종 연결 DoD, `docs/decisions.md` D-145·D-154·D-156·D-158.

## Global Constraints

- `validation/` 내부와 `models/basic/`은 수정하지 않는다.
- 컨설턴트에는 `check_regulation` 노드를 추가하지 않는다.
- 보안1 block은 LLM 호출 전에 종료한다.
- 보안1 warn은 `blocked/reask/need_clarification`로 종료한다.
- 보안2는 summary·actions[].content·reasons[]를 각각 검사한다.
- 보안2 warn은 `masked_text`를 정확한 필드에 반영하고, block은 즉시 종료한다.
- self_check warn은 로그만 남기고 통과한다.
- self_check reject는 `self_check_retry_count`로 전략 재생성 1회만 허용하고 재실패 시 error로 종료한다.
- 전략 프롬프트에는 근거 없는 최상급·질병 효능 표현 금지 문구만 추가한다.

---

### Task 1: 입력 보안 판정 반영

**Files:**
- Modify: `models/consult/nodes/security_input.py`
- Modify: `models/consult/graph/build_consultant.py`
- Test: `models/consult/tests/nodes/test_security_input.py`
- Test: `models/consult/tests/graph/test_build_consultant.py`

**Interfaces:**
- Consumes: `check_input(text: str) -> {action, message}`.
- Produces: `validation.input`, 필요 시 `status="blocked"`와 `issues`.

- [x] block이 `action="block"`, `reason="illegal_or_injection"`를 남기는 실패 테스트를 작성한다.
- [x] warn이 `action="reask"`, `reason="need_clarification"`를 남기는 실패 테스트를 작성한다.
- [x] 입력 차단 시 question_analysis가 실행되지 않는 그래프 실패 테스트를 작성한다.
- [x] 테스트가 현재 구현에서 실패하는지 확인한다.
- [x] security_input 판정 반영과 조건부 엣지를 최소 구현한다.
- [x] 노드·그래프 테스트를 통과시킨다.

### Task 2: 출력 보안 판정과 마스킹 반영

**Files:**
- Modify: `models/consult/nodes/security_output.py`
- Modify: `models/consult/graph/build_consultant.py`
- Test: `models/consult/tests/nodes/test_security_output.py`
- Test: `models/consult/tests/graph/test_build_consultant.py`

**Interfaces:**
- Consumes: `check_output(text: str) -> {action, message, masked_text}`.
- Produces: 필드별 `validation.output`, 마스킹된 `result`, 또는 blocked 상태.

- [x] summary·각 action·각 reason을 독립 검사하는 실패 테스트를 작성한다.
- [x] warn의 masked_text가 원래 위치에 반영되는 실패 테스트를 작성한다.
- [x] block이 `output_blocked` issue를 남기고 self_check를 건너뛰는 실패 테스트를 작성한다.
- [x] 테스트가 현재 구현에서 실패하는지 확인한다.
- [x] 필드 추출·검사·마스킹과 조건부 엣지를 최소 구현한다.
- [x] 노드·그래프 테스트를 통과시킨다.

### Task 3: self_check 판정과 유한 재생성 루프

**Files:**
- Modify: `models/consult/config.py`
- Modify: `models/consult/graph/state.py`
- Modify: `models/consult/nodes/self_check_node.py`
- Modify: `models/consult/graph/build_consultant.py`
- Test: `models/consult/tests/nodes/test_self_check_node.py`
- Test: `models/consult/tests/graph/test_build_consultant.py`
- Test: `models/consult/tests/graph/test_state.py`

**Interfaces:**
- Consumes: `self_check(result: dict, context: dict) -> {action, reasons, message}`.
- Produces: `validation.self_check`, `self_check_retry_count`, 또는 error 상태와 issue.

- [x] warn이 차단 없이 로그만 남기는 실패 테스트를 작성한다.
- [x] 첫 reject가 재시도 카운터를 1로 올리는 실패 테스트를 작성한다.
- [x] 두 번째 reject가 `status="error"`, `reason="unknown"`을 남기는 실패 테스트를 작성한다.
- [x] 그래프가 첫 reject에서 strategy로 한 번만 돌아가고 재실패 시 종료하는 실패 테스트를 작성한다.
- [x] 테스트가 현재 구현에서 실패하는지 확인한다.
- [x] 재시도 상수·상태 필드·노드 처리·조건부 엣지를 최소 구현한다.
- [x] 노드·그래프·상태 테스트를 통과시킨다.

### Task 4: 전략 프롬프트 안전 문구

**Files:**
- Modify: `models/consult/prompts/strategy.py`
- Test: `models/consult/tests/prompts/test_strategy.py`

**Interfaces:**
- Produces: 전략 생성 시 근거 없는 최상급과 질병 예방·치료 효능 표현을 금지하는 system prompt 규칙.

- [x] 정확한 금지 범주가 프롬프트에 포함되는 실패 테스트를 작성한다.
- [x] 테스트가 현재 프롬프트에서 실패하는지 확인한다.
- [x] SYSTEM_PROMPT에 한 문장만 추가한다.
- [x] 프롬프트 테스트를 통과시킨다.

### Task 5: 통합 검증과 커밋

**Files:**
- Modify: `docs/superpowers/plans/2026-08-27-consult-validation-integration-checklist.md`
- Modify: `docs/superpowers/plans/2026-08-27-consult-validation-integration-context-notes.md`

**Interfaces:**
- Produces: 테스트·린트가 통과한 검증 연동 브랜치.

- [x] `pytest models/consult -q`를 실행한다.
- [x] `ruff check models/consult`를 실행한다.
- [x] diff가 컨설턴트 소유 파일과 계획 문서만 포함하는지 확인한다.
- [x] 논리적 변경 단위로 커밋한다.
