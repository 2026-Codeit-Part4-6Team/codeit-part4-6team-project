# D4 ModelResult Review Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining PR #88 Model→Service schema observability and test-boundary review items on a child branch of D4.

**Architecture:** Keep public request models on `StrictModel` and introduce one `InboundModel` for the four top-level model results only. The inbound base ignores unknown top-level fields while logging field names, and nested result models remain strict.

**Tech Stack:** Python 3.11, Pydantic v2, pytest, standard-library logging, Ruff.

## Global Constraints

- `decisions.md` is the SSOT for policy and numeric conflicts; implementation contracts are the SSOT for field shape.
- Logs contain ignored field names only, never ignored values.
- `_ModelResultEnvelope` does not inherit `InboundModel` and does not emit ignored-field logs.
- `MODEL_RESULT_ADAPTER` keeps the existing `status + chatbot_type` explicit dispatch.
- Public Frontend→Service models keep `extra="forbid"`.

---

### Task 1: Add the inbound result base and ignored-field logging

**Files:**
- Modify: `backend/schemas.py`
- Test: `tests/schemas/test_model_result_extra_policy.py`

**Interfaces:**
- Produces: `InboundModel(BaseModel)` with `extra="ignore"`, `populate_by_name=True` and a before-validator that logs ignored key names.
- Consumes: `BasicModelResult`, `ConsultantModelResult`, `BlockedResult`, `ErrorResult` as the four subclasses.

- [ ] **Step 1: Add failing inheritance and logging tests**

```python
def test_model_results_share_inbound_base():
    assert issubclass(BasicModelResult, InboundModel)
    assert issubclass(ConsultantModelResult, InboundModel)
    assert issubclass(BlockedResult, InboundModel)
    assert issubclass(ErrorResult, InboundModel)


def test_inbound_model_logs_ignored_field_name_without_value(caplog):
    payload = {**basic_payload(), "debug_trace": "secret-diagnostic-value"}
    with caplog.at_level(logging.INFO, logger="backend.schemas"):
        MODEL_RESULT_ADAPTER.validate_python(payload, chatbot_type="basic")
    assert "debug_trace" in caplog.text
    assert "secret-diagnostic-value" not in caplog.text
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `uv run --locked --all-groups pytest tests/schemas/test_model_result_extra_policy.py -q`
Expected: collection/import failure because `InboundModel` is not defined, or assertion failure because ignored keys are not logged.

- [ ] **Step 3: Implement the minimal inbound base**

```python
logger = logging.getLogger(__name__)


class InboundModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _log_ignored_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            known = set(cls.model_fields)
            known.update(
                field.alias for field in cls.model_fields.values() if field.alias
            )
            ignored = set(data) - known
            if ignored:
                logger.info(
                    "%s: 모델 응답의 미정의 필드를 무시했습니다: %s",
                    cls.__name__,
                    sorted(ignored),
                )
        return data
```

Change the four top-level result classes to inherit `InboundModel` and remove their duplicate `model_config` overrides.

- [ ] **Step 4: Re-run focused tests and verify GREEN**

Run: `uv run --locked --all-groups pytest tests/schemas/test_model_result_extra_policy.py tests/schemas/test_model_result_adapter.py -q`
Expected: all selected tests pass and no valid payload produces duplicate ignored-field logs.

- [ ] **Step 5: Commit**

```bash
git add backend/schemas.py tests/schemas/test_model_result_extra_policy.py
git commit -m "refactor: add inbound model result boundary"
```

### Task 2: Pin failure reasons and all nested strict boundaries

**Files:**
- Modify: `tests/schemas/test_consultant_result.py`
- Modify: `tests/schemas/test_model_result_extra_policy.py`

**Interfaces:**
- Consumes: existing `ConsultantModelResult`, `ProposalError`, `ConsultantAction` validation behavior.
- Produces: regression tests that fail if Basic/Consultant separation or nested `extra="forbid"` weakens.

- [ ] **Step 1: Tighten the Basic-payload rejection assertion**

```python
with pytest.raises(ValidationError) as exc_info:
    ConsultantModelResult.model_validate(basic_payload)
missing = {
    error["loc"][0]
    for error in exc_info.value.errors()
    if error["type"] == "missing"
}
assert {"strategy", "reasons"} <= missing
```

- [ ] **Step 2: Add explicit ProposalError and ConsultantAction unknown-field tests**

```python
@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (ProposalError, {"field": "copy", "reason": "timeout", "message": "실패", "debug": 1}),
        (ConsultantAction, {"type": "menu", "content": "메뉴", "debug": 1}),
    ],
)
def test_nested_result_models_reject_unknown_fields(model, payload):
    with pytest.raises(ValidationError):
        model.model_validate(payload)
```

- [ ] **Step 3: Run focused regression tests**

Run: `uv run --locked --all-groups pytest tests/schemas/test_consultant_result.py tests/schemas/test_model_result_extra_policy.py tests/schemas/test_model_result_adapter.py -q`
Expected: all selected tests pass.

- [ ] **Step 4: Run full verification**

Run: `uv run --locked --all-groups pytest`
Expected: all tests pass.

Run: `uv run --locked --group dev ruff check .`
Expected: Ruff exits 0.

- [ ] **Step 5: Commit**

```bash
git add tests/schemas/test_consultant_result.py tests/schemas/test_model_result_extra_policy.py
git commit -m "test: close model result review regressions"
```
