# 검증 함수 계약서 (Validation Contract) v1.2

- **작성자**: 전민재 PM
- **작성일**: 2026-08-12
- **파일 위치**: `docs/validation_contract.md` (단일 소스)
- **구현 위치**: `validation/` (전민재 PM 관리 — 두 챗봇 담당자는 **import만**)
- **연관 문서**: `docs/golden_dataset.md` · `docs/decisions.md` · 서비스 API/DB Contract v0.3

---

## 1. 이 문서를 왜 만드는가

### 1.1 실제로 있었던 일

2026-08-12, 검증 함수 스텁에 이런 코드가 있었다.

```python
return {"action": "pass"/"warn"/"block", ...}   # ← 문자열 나눗셈
```

**`import`는 통과하고 호출하는 순간 `TypeError` 발생했다.** 오류 원인은 명세표의 표기(`허용값: pass / warn / block`)를 코드에 그대로 옮겨서 발생한 실수였다.

해당 오류 발견자는 검증 함수를 **쓰는 쪽**(챗봇 담당)이었다. 개발하는 전민재 PM은 해당 오류를 몰랐고, 쓰는 쪽이 연결하다 알았다.

- **교훈**: 함수 시그니처만 합의하면 부족하다.
- **반환값의 의미·처리 규칙·실패 시 동작**까지 문서로 못 박아야 한다. 그것이 이 계약서다.

### 1.2 이 계약서가 답하는 질문 5가지

```
① 함수 4종은 무엇을 받고 무엇을 돌려주는가
② action 값을 받으면 노드는 무엇을 해야 하는가       ← 가장 중요
③ 어떤 판정이 서비스까지 도달하는가
④ 판정이 크레딧 차감·롤백에 어떻게 연결되는가
⑤ 스텁이 실구현으로 바뀔 때 내 코드를 고쳐야 하는가  ← 답: 아니오
```

---

## 2. 책임 경계

| 구분 | 담당 | 내용 |
| --- | --- | --- |
| **함수 구현** | **전민재 PM** | `validation/` 4종 판정 로직 · 키워드 사전 · 법률 규제 RAG |
| **검증 노드 래핑** | 각 챗봇 담당 | 함수를 LangGraph 노드로 감싸 그래프 연결 |
| **판정 결과 전달** | 각 챗봇 담당 | 서비스 API 응답 형식으로 변환 |
| **크레딧 롤백** | 서비스 개발 담당 | `blocked`·`error` 수신 시 차감분 되돌리기 |

> ⚠️ **`validation/` 내부 로직은 담당자가 임의로 수정하지 않는다.** 필요하면 전민재 PM에게 요청한다.
> 두 챗봇이 같은 파일을 쓰므로, 한쪽이 고치면 다른 쪽이 깨진다.

---

## 3. ★ 핵심 개념 — 판정값은 2층에서 소비된다

> **여기를 이해하지 못하면 노드를 잘못 만든다.**

```
[1층] 노드 내부 처리
      · pass  → 다음 노드로 진행
      · warn  → 재생성 루프 또는 민감정보 마스킹 (상한 내에서 자체 해결)
      · block → 즉시 그래프 종료
              ↓ 자체 해결 실패했을 때만
[2층] 서비스 도달 (최종 응답)
      · status = "blocked" (단일값)
      · action = "block" | "reask" | "warn" (상세)
      · message / alternative (사용자 안내)
```

**왜 두 층인가**

| 문서 | 표현 | 실제 의미 |
| --- | --- | --- |
| `decisions.md` **D-011** | *"blocked 단일화, warn/reask 미노출"* | **1층**: warn은 노드 내부 재생성으로 소화 |
| API Contract **v0.3 §6.5** | *"block/reask/warn 세분화 유지"* | **2층**: 서비스로 나갈 땐 상세를 실어 보냄 |

**두 문서는 충돌이 아니라 서로 다른 층을 말한 것이다.**
대부분의 `warn`은 노드 안에서 재생성으로 해결되고, **재생성 상한(D-019)을 넘겼을 때만** 서비스로 나간다.

---

## 4. 함수 4종 시그니처

```python
# validation/security.py
def check_input(text: str) -> dict: ...
def check_output(text: str) -> dict: ...

# validation/regulation.py
def check_regulation(copy: str) -> dict: ...

# validation/self_check.py
def self_check(result: dict, context: dict) -> dict: ...
```

| 함수 | 입력 | 유효성 검사 대상 | 파이프라인 위치 |
| --- | --- | --- | --- |
| `check_input` | 사용자 질문 | **입력** — 불법 키워드·프롬프트 인젝션 | 맨 앞 (LLM 모델 API 호출 전) |
| `check_regulation` | 생성된 카피 | **출력** — 표시광고법·식품표시광고법 등. | 카피 생성 직후 |
| `check_output` | 최종 답변 | **출력** — 민감정보·시스템 프롬프트 누출 | 응답 직전 |
| `self_check` | 결과 + 컨텍스트 | **품질** — LLM 모델 답변 근거 유무·완결성 | 맨 끝 |

> **`check_input`만 "막는" 유효성 검사(Validation)이고, 나머지는 "고쳐서 내보내는" 유효성 검사(Validation)이다.**
> 그래서 `check_input`은 LLM 모델 호출 **전**에 두어 유효성 검사 결과 입력된 데이터 올바르지 않은 경우 LLM 모델을 호출하지 않으므로 LLM 모델 API 호출 횟수 0회, 호출 비용을 0원으로 만든다.

---

## 5. 반환 규격

### 5.1 `check_input` / `check_output`

```python
# check_input
{
    "action": "pass",      # "pass" | "warn" | "block"
    "message": ""          # 사용자 안내 문구 (pass면 빈 문자열)
}

# check_output — masked_text 가 하나 더 있다
{
    "action": "warn",
    "message": "연락처로 보이는 정보를 가렸습니다.",
    "masked_text": "문의는 010-****-**** 로 주세요"
}
```

| 함수 | 필드 | 타입 | 필수 | Nullable | 설명 |
| --- | --- | --- | --- | --- | --- |
| 공통 | `action` | string | O | X | `pass` \| `warn` \| `block` |
| 공통 | `message` | string | O | X | 사용자 표시 문구. `pass`일 때 `""` |
| **`check_output`만** | `masked_text` | string | O | X | **`pass`면 입력 원문 그대로**, `warn`이면 민감정보 마스킹본, `block`이면 `""` |

> ★ **`masked_text` 가 없으면 §6.3의 민감정보 마스킹 규칙은 구현할 수 없다.**
> 노드는 "민감정보가 있다"는 사실만 알고 *어디가* 민감정보인지 모르기 때문이다.
> 민감정보 마스킹 규칙을 `validation/` 이 관리하는 이유는 §13-③과 같다 —
> 두 챗봇이 각자 정규식을 만들면 민감정보 마스킹 처리하는 범위가 달라진다.
> `check_output` 은 키워드 매칭(LLM 모델 API 호출 횟수 0회)이라 **텍스트 조각별로 여러 번 호출해도 비용이 없다.**

### 5.2 `check_regulation`

```python
{
    "action": "warn",
    "law": "표시광고법 제3조",
    "reason": "객관적 근거 없는 최상급 표현",
    "alternative": "정성껏 볶은 원두",
    "message": "'최고'는 부당광고가 될 수 있어요. 다른 표현을 제안드릴까요?"
}
```

| 필드 | 타입 | 필수 | Nullable | 설명 |
| --- | --- | --- | --- | --- |
| `action` | string | O | X | `pass` \| `warn` \| `block` |
| `law` | string | O | X | 근거 법률 조문. `pass`면 `""` |
| `reason` | string | O | X | 왜 문제인지. `pass`면 `""` |
| `alternative` | string | O | X | **대안 문구**. `pass`면 `""` |
| `message` | string | O | X | 사용자 안내. `pass`면 `""` |

> ★ **`alternative`가 이 함수의 존재 이유다.**
> *"'최고'는 쓸 수 없습니다"* 만 주면 사용자는 *"그럼 뭘 쓰라고?"* 가 된다.
> **차단이 아니라 대안 제시가 목적**이므로, `warn`일 때 `alternative`는 반드시 채워진다.

> ⚠️ **`law` · `alternative` 는 서비스 응답 계약(v0.3 §6.5)에 없는 필드다.**
> `BlockedResult` 는 `{status, action, reason, message}` 4개만 정의하고
> `extra="ignore"`(D-059) 이므로, 그대로 올려 보내면 **에러 없이 버려진다.**
> 따라서 **`message` 안에 대안 문구를 문장으로 포함한다.**
>
> ```
> ✅ "'최고'는 객관적 근거가 없으면 부당광고가 될 수 있어요.
>     대신 '정성껏 볶은 원두'는 어떨까요?"
> ❌ "'최고'는 사용할 수 없습니다."   ← 사용자가 뭘 써야 할지 모른다
> ```
>
> `law` · `alternative` 필드 자체는 **모델 내부 상태(`validation.regulation`)와
> 골든 데이터셋 평가용으로 유지**한다. 서비스 응답에 별도 필드로 싣는 안은
> D5 프론트엔드 UI/UX 작업 시 v0.3 계약 변경(D-046 절차)으로 검토한다.

### 5.3 `self_check`

```python
{
    "action": "reject",
    "reasons": ["답변 근거 없음", "답변 제안 개수 부족"],
    "message": "생성 결과에 답변 근거가 부족합니다."
}
```

| 필드 | 타입 | 필수 | Nullable | 설명 |
| --- | --- | --- | --- | --- |
| `action` | string | O | X | `pass` \| `warn` \| **`reject`** |
| `reasons` | string[] | O | X | 실패 사유 목록. `pass`면 `[]` |
| `message` | string | O | X | 사용자 안내. `pass`면 `""` |

> ⚠️ **`self_check`만 세 번째 값이 `block`이 아니라 `reject`다.**
> 보안·규제는 "막는다(block)"이고, 품질은 "되돌린다(reject)"라 의미가 다르다.

### 5.4 ⚠️ 절대 규칙 3가지

```
① action 값은 문자열 하나만 반환한다
   ✅ "action": "pass"
   ❌ "action": "pass"/"warn"/"block"     ← 파이썬에서 TypeError

② pass일 때도 모든 필드를 채운다 (빈 문자열/빈 배열)
   ✅ {"action":"pass", "law":"", "reason":"", "alternative":"", "message":""}
   ❌ {"action":"pass"}                    ← 받는 쪽이 KeyError

③ 받는 쪽은 message를 직접 만들지 않는다
   전민재 PM이 준 message를 그대로 사용자에게 전달한다
   → 안내 문구가 팀마다 달라지면 서비스 톤이 무너진다
```

---

## 6. ★ action 값별 노드 처리 규칙

> **이 표가 검증 함수 계약서의 본체다.** 검증 노드를 만들 때 이대로 구현한다.

### 6.1 `check_input` (보안1)

| action | 노드가 할 일 | 서비스 도달 | 크레딧 |
| --- | --- | --- | --- |
| `pass` | 다음 노드로 진행 | — | — |
| `warn` | **사용자에게 재질문 후 그래프 종료** | ✅ `status="blocked"`, `action="reask"` | **롤백** |
| `block` | **즉시 종료. LLM 모델 API 호출 횟수 0회, 호출 비용 0원** | ✅ `status="blocked"`, `action="block"` | **롤백** |

> **`block`에서 LLM 모델 API를 호출하지 않는 것이 핵심이다.** 여기서 막아야 LLM 모델 API 호출 횟수 0회, 호출 비용이 0원이다.

### 6.2 `check_regulation` (법률 규제 검증)

| action | 노드가 할 일 | 서비스 도달 | 크레딧 |
| --- | --- | --- | --- |
| `pass` | 다음 노드로 진행 | — | 차감 유지 |
| `warn` (**상한 내 해결**) | **카피 재생성 → 통과하면 정상 진행 (상한 2회 — D-019)** | — | 차감 유지 |
| `warn` (**상한 초과**) | **대안을 담은 message와 함께 종료** | ✅ `status="blocked"`, `action="warn"` | **롤백** |
| `block` | 즉시 종료 | ✅ `status="blocked"`, `action="block"` | **롤백** |

> ⚠️ **상한 초과는 `blocked` 이므로 §7에 따라 반드시 롤백한다.**
> 사용자는 광고 카피를 받지 못했다 — D-020의 *"카피가 핵심 산출물"* 기준으로도 0개다.

**재생성 루프 상세**
```
카피 생성 → check_regulation → warn
   ↓ (1회차 재생성)
카피 생성 → check_regulation → warn
   ↓ (2회차 재생성 — 상한)
카피 생성 → check_regulation → warn
   ↓ 상한 초과
서비스 반환: status="blocked", action="warn",
            law·reason·alternative 포함
```

> **상한을 두는 이유**: 무한 재생성 기능 구현 및 실행 시 OpenAI $30 예산 한도를 조기 소진한다.
> 2회 초과 시 사용자에게 **대안 문구를 주고 판단을 사용자에게 넘긴다.**

### 6.3 `check_output` (보안2)

| action | 노드가 할 일 | 서비스 도달 | 크레딧 |
| --- | --- | --- | --- |
| `pass` | 다음 노드로 진행 | — | 차감 유지 |
| `warn` | **`masked_text` 로 해당 텍스트를 교체하고 진행** | — | 차감 유지 |
| `block` | 즉시 종료 | ✅ `status="blocked"` | **롤백** |

> `warn` 은 *"담당자 개인 전화번호가 노출됐다"* 같은 경우다. 최종 답변 전체를 버릴
> 필요는 없고, `check_output` 이 돌려준 **`masked_text` 로 갈아끼운다.**
> 노드가 직접 정규식으로 가리지 않는다(§5.1 참조).

### 6.4 `self_check` (답변 검증)

| action | 노드가 할 일 | 서비스 도달 | 크레딧 |
| --- | --- | --- | --- |
| `pass` | LLM 모델 답변 반환 | — | 차감 유지 |
| `warn` | **로그만 남기고 LLM 모델 답변 반환** | — | 차감 유지 |
| `reject` | **재생성 1회 → 실패 시 error** | 재시도 실패 시 ✅ | **롤백** |

> `self_check`의 `warn`은 *"LLM 모델 답변의 근거가 좀 약하다"* 수준이라 **사용자에게 보여줘도 된다.**
> `reject`는 *"근거가 아예 없다"* 라 되돌린다.

---

## 7. 크레딧 롤백 규칙 (서비스 개발 담당 전용)

> 서비스 핵심 비즈니스 로직은 **LLM/이미지 생성 모델 호출 전에 크레딧을 차감**한다(서비스 SDP §6.5).
> 따라서 아래 경우 **반드시 롤백**해야 한다. (서비스 API/DB Contract v0.3 -> S-11 · docs/decisions.md -> D-020 연계)

| LLM/이미지 생성 모델 응답 | 크레딧 | 무료 횟수 | 근거 |
| --- | --- | --- | --- |
| `status="ok"` (카피 1개 이상 성공) | **차감 유지** | 차감 유지 | D-020 |
| `status="ok"` (이미지만 실패) | **차감 유지** | 차감 유지 | D-020 — 카피가 핵심 산출물 |
| **`status="blocked"`** | **전액 롤백** | **롤백** | 사용자가 결과물을 못 받음 |
| **`status="error"`** | **전액 롤백** | **롤백** | 서비스 API/DB Contract v0.3 -> S-11 |

> ⚠️ **`blocked`도 롤백 대상이다.** `error`만 롤백하도록 구현하면,
> 불법 키워드를 입력한 사용자가 **크레딧만 잃고 아무것도 못 받는다.** 컴플레인 1순위.

**reask 왕복 시 크레딧 관련 과금 구조 (v0.3 §6.5 연계)**

```
1차 요청 → 차감 → check_input warn / question_analysis 질문 분석 결과: 정보부족
        → status="blocked", action="reask" → 롤백
2차 요청 → extra.clarification 추가 + 새 Idempotency-Key
        → 다시 차감 → 정상 생성
```

> v0.3 §6.5는 *"reask 응답 자체는 크레딧 관련 과금을 완료하지 않는다"* 라고 쓰지만,
> 서비스는 **LLM/이미지 생성 모델 호출 전에 차감**하므로(§9.1) 실제 구현은 **롤백**이다. 결과는 같다.
>
> ⚠️ **reask 는 무료가 아니라 왕복이다.** 후속 요청은 새 Idempotency-Key라
> 새로운 차감이 일어난다. 따라서 **reask 남발하면 사용자 크레딧이 계속 소모된다.**
> 실제로 기본 챗봇 D3에서 *"여름 신메뉴 홍보 문구"* 처럼 충분한 질문까지
> reask 처리되는 문제가 있었다 — 판단이 애매하면 **충분함(pass)** 이 기본값이다.

---

## 8. 검증 노드 래핑 예시 (두 챗봇 담당자 전용)

> 함수 내부가 스텁이든 실구현이든 **노드 코드는 동일하다.**
> 아래 예시는 `models/basic/`·`models/consult/` 양쪽에 그대로 적용된다.

### 8.0 ⚠️ 모든 검증 노드가 지키는 4가지

```
① 부분 업데이트만 반환한다 — state 를 제자리 수정하지 않고 통째로 반환하지 않는다
   ✅ return {"validation": {...}}
   ❌ state["x"] = 1; return state        ← 리듀서 중복 병합·병렬 덮어쓰기

② validation 은 반드시 기존 값과 병합해서 반환한다
   ✅ {"validation": {**state.get("validation", {}), "input": verdict}}
   ❌ {"validation": {"input": verdict}}  ← 앞 노드 판정이 사라질 수 있다

③ 차단 결과는 issues 리스트에 append 한다 (status 는 문자열 하나)
   updates["issues"] = state.get("issues", []) + [{...}]

④ 라우팅 신호로 새 키를 만들지 않는다
   ❌ state["_goto"] = "copy_gen"          ← 스키마에 없는 키는 버려진다
   ✅ status · validation · *_retry_count 등 선언된 필드로 라우터가 판단
```

**공통 상태 필드** (`models/shared/state_common.py`)

| 필드 | 타입 | 용도 |
| --- | --- | --- |
| `status` | `"ok"` \| `"blocked"` \| `"error"` | 최종 상태 |
| `issues` | `list[dict]` | `{source, action, reason, message}` 누적 |
| `validation` | `dict` | 함수별 원본 판정 보관 |
| `copy_retry_count` | `int` | 법률 규제 재생성 카운터 (기본 챗봇) |
| `self_check_retry_count` | `int` | self_check 재생성 카운터 |

> ★ **재시도 카운터는 용도별로 분리한다.** 하나를 공유하면 법률 규제 재생성이 카운터를
> 소진해 self_check 재생성 기회가 사라진다.

---

### 8.1 보안1 노드 — 기본·컨설턴트 공통

```python
# models/basic/nodes/security_input.py
# models/consult/nodes/security_input.py
from validation.security import check_input


def security_input_node(state: dict) -> dict:
    """보안1 — check_input() 을 그래프 노드로 감싼다.

    block → 즉시 종료. 이 지점에서 막아야 LLM 모델 API 호출 횟수 0회·비용 0원이다.
    warn  → 정보 부족으로 보고 재질문(reask) 후 종료.
    """
    verdict = check_input(state["question"])
    updates: dict = {
        "validation": {**state.get("validation", {}), "input": verdict}
    }

    action = verdict["action"]
    if action == "pass":
        return updates

    # warn·block 모두 그래프를 끝낸다 — 서비스에는 action 으로 구분해 전달한다
    updates["status"] = "blocked"
    updates["issues"] = state.get("issues", []) + [
        {
            "source": "input",
            "action": "block" if action == "block" else "reask",
            "reason": "illegal_or_injection" if action == "block" else "need_clarification",
            "message": verdict["message"],
        }
    ]
    return updates
```

---

### 8.2 법률 규제 검증 노드 — **기본 챗봇 전용** (§8.6 참조)

```python
# models/basic/nodes/regulation_node.py
from validation.regulation import check_regulation

MAX_COPY_RETRY = 2  # D-019 카피 재생성 상한


def regulation_node(state: dict) -> dict:
    """법률 규제 검증 — 카피 3안을 각각 판정한다.

    · pass·warn 카피는 그대로 살린다(warn 은 대안 제시가 목적이지 삭제가 아니다)
    · block 카피는 배열에서 빼지 않고 error 슬롯으로 치환한다 (D-018·3안 고정)
    · 살아남은 카피가 하나도 없을 때만 재생성 루프로 되돌린다
    """
    ranked = state.get("ranked_copies", [])
    checked, verdicts = [], []

    for item in ranked:
        copy_text = item.get("copy")
        if not copy_text:                      # 이미 실패한 슬롯은 판정 대상이 아니다
            checked.append(item)
            verdicts.append(None)
            continue

        verdict = check_regulation(copy_text)
        verdicts.append(verdict)

        if verdict["action"] == "block":
            checked.append({                   # ★ 자리를 비우지 않는다
                "copy": None,
                "image_b64": None,
                "error": {
                    "field": "copy",
                    "reason": "content_policy",
                    "message": verdict["message"],
                },
            })
        else:
            checked.append(item)               # pass·warn 은 유지

    updates: dict = {
        "ranked_copies": checked,
        "validation": {**state.get("validation", {}), "regulation": verdicts},
    }

    if any(c.get("copy") for c in checked):    # 하나라도 살아남음 → 통과
        return updates

    retry = state.get("copy_retry_count", 0)
    if retry < MAX_COPY_RETRY:
        updates["copy_retry_count"] = retry + 1
        return updates                         # 라우터가 copy_gen 으로 되돌린다

    # 상한 초과 — 대안(alternative)을 함께 주고 판단을 사용자에게 넘긴다
    worst = next((v for v in verdicts if v and v["action"] != "pass"), None)
    updates["status"] = "blocked"
    updates["issues"] = state.get("issues", []) + [
        {
            "source": "regulation",
            "action": worst["action"] if worst else "block",
            "reason": "regulation_risk",
            "law": worst["law"] if worst else "",
            "alternative": worst["alternative"] if worst else "",
            "message": worst["message"] if worst else "법률 규제 검증을 통과하지 못했습니다.",
        }
    ]
    return updates
```

---

### 8.3 보안2 노드 — 기본·컨설턴트

- **warn 은 텍스트 전체를 버리지 않고 `masked_text` 로 교체한다**(V-02).
- 민감정보 마스킹 규칙은 `validation/` 이 관리한다 — 두 챗봇이 각자 정규식을 만들면
민감정보 마스킹 처리하는 범위가 달라진다(§13-③과 같은 이유).
- `check_output` 은 키워드 매칭(LLM 모델 API 호출 횟수 0회)이라 **조각별로 여러 번 호출해도 LLM 모델 API 호출 비용이 없다.**

**공통 본체**

```python
# models/basic/nodes/security_output.py
# models/consult/nodes/security_output.py
from validation.security import check_output


def security_output_node(state: dict) -> dict:
    """보안2 — 사용자에게 나갈 모든 텍스트 조각을 검증·민감정보 마스킹한다."""
    parts = _outbound_parts(state)             # [(경로, 텍스트), ...] — 챗봇별 구현
    verdicts, replacements = {}, {}

    for path, text in parts:
        if not text:
            continue
        verdict = check_output(text)
        verdicts[path] = verdict

        if verdict["action"] == "block":
            return {
                "validation": {**state.get("validation", {}), "output": verdicts},
                "status": "blocked",
                "issues": state.get("issues", []) + [
                    {
                        "source": "output",
                        "action": "block",
                        "reason": "sensitive_leak",
                        "message": verdict["message"],
                    }
                ],
            }
        if verdict["action"] == "warn":
            replacements[path] = verdict["masked_text"]

    updates: dict = {
        "validation": {**state.get("validation", {}), "output": verdicts}
    }
    if replacements:
        updates.update(_apply_mask(state, replacements))   # 챗봇별 구현
    return updates
```

**기본 챗봇 — 검증 대상은 카피 3안**

```python
# models/basic/nodes/security_output.py
def _outbound_parts(state: dict) -> list[tuple[str, str]]:
    return [
        (f"proposals[{i}]", c["copy"])
        for i, c in enumerate(state.get("ranked_copies", []))
        if c.get("copy")
    ]


def _apply_mask(state: dict, replacements: dict) -> dict:
    ranked = [dict(c) for c in state.get("ranked_copies", [])]
    for path, masked in replacements.items():
        ranked[int(path[len("proposals["):-1])]["copy"] = masked
    return {"ranked_copies": ranked}
```

**컨설턴트 — 검증 대상은 summary + actions + reasons (D-145)**

```python
# models/consult/nodes/security_output.py
def _outbound_parts(state: dict) -> list[tuple[str, str]]:
    result = state.get("result") or {}
    parts = [("summary", result.get("summary", ""))]
    parts += [(f"actions[{i}]", a["content"])
              for i, a in enumerate(result.get("actions", []))]
    parts += [(f"reasons[{i}]", r)
              for i, r in enumerate(result.get("reasons", []))]
    return parts


def _apply_mask(state: dict, replacements: dict) -> dict:
    result = state.get("result") or {}
    masked = {
        "summary": replacements.get("summary", result.get("summary", "")),
        "actions": [
            {**a, "content": replacements.get(f"actions[{i}]", a["content"])}
            for i, a in enumerate(result.get("actions", []))
        ],
        "reasons": [
            replacements.get(f"reasons[{i}]", r)
            for i, r in enumerate(result.get("reasons", []))
        ],
    }
    return {"result": masked}
```

> ⚠️ **`summary` 만 검증하면 안 된다.** `actions[].content` 와 `reasons[]` 도
> 사용자 화면에 그대로 노출된다.

---

### 8.4 self_check 노드 — 기본·컨설턴트 공통

```python
# models/basic/nodes/self_check_node.py
# models/consult/nodes/self_check_node.py
import logging

from validation.self_check import self_check

logger = logging.getLogger(__name__)
MAX_SELF_CHECK_RETRY = 1  # V-03 - self_check 재생성 상한


def self_check_node(state: dict) -> dict:
    """self_check — LLM 모델 답변 근거 유무·완결성을 판정한다.

    warn   → 로그만 남기고 그대로 반환한다(LLM 모델 답변 근거가 약할 뿐 사용자에게 보여줘도 된다).
    reject → 생성 노드로 1회 되돌린다. 실패하면 status="error".
    """
    verdict = self_check(state.get("result") or {}, state.get("context") or {})
    updates: dict = {
        "validation": {**state.get("validation", {}), "self_check": verdict}
    }

    action = verdict["action"]
    if action == "pass":
        return updates

    if action == "warn":
        logger.info("self_check warn — LLM 모델 답변 근거가 약하지만 반환한다: %s", verdict["reasons"])
        return updates

    retry = state.get("self_check_retry_count", 0)
    if retry < MAX_SELF_CHECK_RETRY:
        updates["self_check_retry_count"] = retry + 1
        return updates                         # 라우터가 생성 노드로 되돌린다

    updates["status"] = "error"
    updates["issues"] = state.get("issues", []) + [
        {
            "source": "self_check",
            "action": "reject",
            "reason": "unknown",               # ★ ErrorResult.reason enum 안에서 고른다
            "message": verdict["message"],
        }
    ]
    return updates
```

> ⚠️ **`reason` 은 서비스 API/DB Contract v0.3 `ErrorResult` 의 4종
> (`timeout`·`rate_limit`·`provider_error`·`unknown`) 중 하나여야 한다.**
> `self_check_failed` 같은 값을 쓰면 서비스에서 검증 실패로 502가 난다.

---

### 8.5 조건부 엣지 연결

> **`path_map`(세 번째 인자)은 필수다.** 라우터가 `END` 로 보내려면
> `from langgraph.graph import END` 센티널을 매핑해야 한다 — `"END"` 문자열은 동작하지 않는다.

**기본 챗봇**

```python
# models/basic/graph/build_basic.py
from langgraph.graph import END


def route_after_security_input(state: dict) -> str:
    return "end" if state.get("status") == "blocked" else "question_analysis"


def route_after_regulation(state: dict) -> str:
    if state.get("status") in ("blocked", "error"):
        return "end"
    if not any(c.get("copy") for c in state.get("ranked_copies", [])):
        return "copy_gen"                      # 재생성 루프
    return "image_gen"


def route_after_self_check(state: dict) -> str:
    if state.get("status") in ("blocked", "error"):
        return "end"
    verdict = (state.get("validation") or {}).get("self_check") or {}
    return "copy_gen" if verdict.get("action") == "reject" else "end"


graph.add_conditional_edges(
    "security_input", route_after_security_input,
    {"question_analysis": "question_analysis", "end": END},
)
graph.add_conditional_edges(
    "regulation", route_after_regulation,
    {"copy_gen": "copy_gen", "image_gen": "image_gen", "end": END},
)
graph.add_conditional_edges(
    "self_check", route_after_self_check,
    {"copy_gen": "copy_gen", "end": END},
)
```

**컨설턴트 챗봇**

```python
# models/consult/graph/build_consultant.py
from langgraph.graph import END


def route_after_security_input(state: dict) -> str:
    return "end" if state.get("status") == "blocked" else "question_analysis"


def route_after_security_output(state: dict) -> str:
    return "end" if state.get("status") == "blocked" else "self_check_node"


def route_after_self_check(state: dict) -> str:
    if state.get("status") in ("blocked", "error"):
        return "end"
    verdict = (state.get("validation") or {}).get("self_check") or {}
    return "strategy" if verdict.get("action") == "reject" else "end"


graph.add_conditional_edges(
    "security_input", route_after_security_input,
    {"question_analysis": "question_analysis", "end": END},
)
graph.add_conditional_edges(
    "security_output", route_after_security_output,
    {"self_check_node": "self_check_node", "end": END},
)
graph.add_conditional_edges(
    "self_check_node", route_after_self_check,
    {"strategy": "strategy", "end": END},
)
```

> ⚠️ **재생성 루프는 사이클이다.** LangGraph 기본 `recursion_limit` 은 25이므로,
> 재시도 상한(`MAX_COPY_RETRY`·`MAX_SELF_CHECK_RETRY`)을 반드시 지켜야
> `GraphRecursionError` 로 끝나지 않는다.

---

### 8.6 챗봇별 감싸는 함수 — 왜 컨설턴트는 3종인가

| 함수 | 기본 챗봇 | 컨설턴트 | 근거 |
| --- | --- | --- | --- |
| `check_input` | ✅ | ✅ | 사용자 질문은 양쪽 동일 |
| `check_regulation` | ✅ | **❌ 미구현** | 아래 참조 |
| `check_output` | ✅ | ✅ | 양쪽 다 사용자에게 텍스트가 나감 |
| `self_check` | ✅ | ✅ | 양쪽 다 LLM 모델 답변 근거·완결성 필요 |

**컨설턴트에 법률 규제 검증 노드를 두지 않는 이유**

```
① §4 표 정의: check_regulation 의 입력은 "생성된 카피", 위치는 "카피 생성 직후".
   컨설턴트는 카피를 만들지 않는다(전략 조언 = strategy.summary·actions·reasons).
② 표시광고법은 "광고"에 적용된다. 컨설팅 조언 자체는 광고가 아니다.
③ 컨설턴트 전략이 광고가 되는 경로는 [이 전략으로 광고 만들기](link_to_ads) 하나뿐이고,
   그 결과물은 source_gen_id 로 기본 챗봇 파이프라인을 타면서 regulation_node 를 통과한다.
④ 붙이면 warn 시 전략 재생성 루프가 생겨 LLM 모델 API 호출이 늘고 $30 예산을 압박한다.

단, 컨설턴트가 "이 지역 최고 카페로 포지셔닝하세요" 같은 표현을 낼 수 있으므로
strategy SYSTEM_PROMPT 에 아래 한 줄을 둔다(LLM 모델 API 호출 0회·법률 규제 검증 노드 0개):
  "'최고'·'유일'·'1등' 같은 근거 없는 최상급 표현과 질병 예방·치료 효능 표현은 쓰지 않는다."
```

---

## 9. 스텁 → 실구현 전환

> ★ **핵심 원칙: 반환 형식이 같으므로 받는 쪽 코드는 수정할 필요가 없다.**

| 함수 | 현재 상태 | 실구현 예정 | 실구현 시 달라지는 것 |
| --- | --- | --- | --- |
| `check_input` | 스텁(`pass`) | **8/19** | 실제 `block`·`warn` 반환 시작 |
| `check_regulation` 1단 | 스텁(`pass`) | **8/19** | 키워드 기반 `warn` + `alternative` 반환 |
| `check_output` | 스텁(`pass`) | **8/19** | `masked_text` 채워짐, 민감정보 누출 탐지 시 `warn`이면 민감정보 마스킹본, `block`이면 `""` |
| `self_check` (A)규칙 | 스텁(`pass`) | **8/19** | LLM 모델 답변 근거·개수·길이 검사 시작 |
| `check_regulation` 2단 RAG | 미구현 | **8/20** [SHOULD] | `law`·`alternative`가 법률 조문 기반으로 채워짐 |

> **일정 변경 사유(D-142)**: 당초 8/12~8/14였으나 4종 모두 미착수 상태였다.
> `golden_dataset.md` 의 **거부 문항 15개(R-)** 가 이 실구현을 전제하므로
> 8/19로 그대로 유지하고, 이후 지연되면 R- 문항 평가 자체가 불가능하다.


**전환 시 전민재 PM이 할 일**
```
① validation/ 내부만 수정
② 반환 형식은 그대로 유지 (필드 추가·삭제 금지)
③ 팀 채널에 "○○ 실구현 완료" 공지
④ decisions.md 의사결정 로그 기록
```

**전환 시 두 챗봇 담당자가 할 일**
```
아무것도 없음. 다만 실구현 후 자기 파이프라인을 한 번 돌려
warn/block 분기가 정상 동작하는지 확인한다.
```

---

## 10. 계약 위반 방지 — 스모크 테스트

> `tests/validation/test_contract.py` 가 해당 계약을 자동 검증한다. **CI에서 매 PR마다 실행된다.**

```python
"""검증 함수 4종 계약 스모크 테스트 — 스텁이든 실구현이든 항상 통과해야 함"""
from validation.regulation import check_regulation
from validation.security import check_input, check_output
from validation.self_check import self_check


def test_check_input():
    r = check_input("테스트 질문")
    assert r["action"] in ("pass", "warn", "block")
    assert isinstance(r["message"], str)


def test_check_output():
    r = check_output("테스트 답변")
    assert r["action"] in ("pass", "warn", "block")
    assert isinstance(r["message"], str)


def test_check_regulation():
    r = check_regulation("우리 가게가 최고입니다")
    assert r["action"] in ("pass", "warn", "block")
    for k in ("law", "reason", "alternative", "message"):
        assert isinstance(r[k], str), f"{k} 는 문자열이어야 함"


def test_check_output_returns_masked_text():
    """check_output 은 masked_text 를 반드시 채운다 — 노드가 이 값으로 갈아끼운다."""
    r = check_output("문의는 010-1234-5678 로 주세요")
    assert r["action"] in ("pass", "warn", "block")
    assert isinstance(r["masked_text"], str)
    if r["action"] == "pass":
        assert r["masked_text"] == "문의는 010-1234-5678 로 주세요"   # pass면 원문 그대로


def test_check_regulation_message_contains_alternative_on_warn():
    """warn 이면 message 안에 대안이 문장으로 들어가야 한다 — 별도 필드는 서비스에서 버려진다."""
    r = check_regulation("우리 가게가 최고입니다")
    if r["action"] == "warn":
        assert r["alternative"], "alternative 가 비어 있으면 대안 제시율 지표가 0이 된다"
        assert r["alternative"] in r["message"], "대안이 message 에 포함돼야 사용자에게 도달한다"


def test_self_check():
    r = self_check({"proposals": []}, {})
    assert r["action"] in ("pass", "warn", "reject")
    assert isinstance(r["reasons"], list)
    assert isinstance(r["message"], str)
```

> **이 테스트가 잡는 것**: 반환 타입 오류, 필드 누락, `action` 오타.
> **import만으로는 안 잡힌다** — 반드시 **호출**해야 잡히므로 함수를 실제로 실행한다.

**실행**
```bash
uv run --locked --all-groups pytest tests/validation/test_contract.py -q
uv run --locked --group dev ruff check . --fix
```

---

## 11. 골든 데이터셋과의 연결

> 이 계약이 **실제로 잘 지켜지는지**는 골든 데이터셋 거부 영역(`R-` 15문항)이 검증한다.
> 상세는 `docs/golden_dataset.md` §3.4 참조.

| 골든 문항 | 검증 대상 함수 | 기대 `action` |
| --- | --- | --- |
| `R-001`~`R-003` (불법 품목) | `check_input` | `block` |
| `R-004`~`R-005` (프롬프트 인젝션) | `check_input` | `block` |
| `R-006`~`R-008` (과장 표현) | `check_regulation` | `warn` + `alternative` |
| `R-009`~`R-010` (의학 효능) | `check_regulation` | `warn` + `alternative` |
| **`R-011`~`R-015` (과잉 차단 가드)** | `check_input`·`check_regulation` | **`pass`** |

**측정 지표**

| 지표 | 계산 | 목표 |
| --- | --- | --- |
| 차단 정확도(Recall) | `R-001`~`R-010` 중 정답 일치 비율 | **100%** (불법은 하나도 놓치면 안 됨) |
| **과잉 차단률(FPR)** | `R-011`~`R-015` 중 잘못 막은 비율 | **10% 이하** |
| 대안 제시율 | `warn` 판정 중 `alternative` 채워진 비율 | **100%** |

> ⚠️ **차단 문항만 있으면 "전부 막는 함수"도 100점을 받는다.**
> 과잉 차단 가드 5문항이 실제 품질을 드러낸다.

---

## 12. 서비스 API 계약과의 매핑

> 검증 노드가 `state["issues"]` 에 쌓은 항목을 서비스 응답으로 어떻게 바꾸는지.
> 서비스 API/DB Contract v0.3 §6.5 · §6.6 기준.

**모델 → 서비스 정책 응답 구조**
```json
{
  "status": "blocked",
  "action": "warn",
  "reason": "regulation_risk",
  "message": "'최고'와 같은 표현은 부당광고가 될 수 있어요. 다른 표현을 제안드릴까요?"
}
```

### 12.1 ⚠️ `status` 는 세 가지가 따로 있다 (v0.3 §7)

| 구분 | 값 | 관리 |
| --- | --- | --- |
| **Model status** | `ok` \| `blocked` \| `error` | 본 계약서가 다루는 값. `state["status"]` |
| Generation status | `pending` \| `generating` \| `done` \| `failed` \| `published` | 서비스 생명주기 |
| HTTP status | 200 · 402 · 422 · 502 · 504 … | REST 처리 결과 |

> **셋을 섞어 쓰지 않는다.** 모델 노드는 Model status만 세팅한다.

### 12.2 판정 → 서비스 응답 매핑

| 검증 함수 결과 | 서비스 도달 | `status` | `action` | `reason` |
| --- | --- | --- | --- | --- |
| `check_input` → `block` | ✅ | `blocked` | `block` | `illegal_or_injection` |
| `check_input` → `warn` | ✅ | `blocked` | `reask` | `need_clarification` |
| `check_regulation` → `block` | ✅ | `blocked` | `block` | `prohibited_item` |
| `check_regulation` → `warn` (상한 내 해결) | ❌ | — | — | — |
| `check_regulation` → `warn` (상한 초과) | ✅ | `blocked` | `warn` | `regulation_risk` |
| `check_output` → `block` | ✅ | `blocked` | `block` | `sensitive_leak` |
| `check_output` → `warn` (마스킹 성공) | ❌ | — | — | — |
| `self_check` → `warn` | ❌ | — | — | — |
| `self_check` → `reject` (재시도 실패) | ✅ | **`error`** | — | **`unknown`** |

> **`self_check` 실패만 `error`인 이유**: 보안·규제는 *"의도적으로 막았다"* 이고,
> 품질 실패는 *"LLM 모델 답변 만들지 못했다"* 라 성격이 다르다. HTTP 매핑도 달라진다.
> ★ **`self_check` 실패의 `reason` 은 반드시 `unknown` 이다.**
> v0.3 §6.6 `ErrorResult.reason` 은 **`timeout` · `rate_limit` · `provider_error` · `unknown`
> 4종 enum**이다. `self_check_failed` 같은 값을 쓰면 서비스 Pydantic 검증이 실패해
> 사용자에게 **502**가 나간다. (D-073과 동일한 사고 유형)

### 12.3 `reason` 코드 목록 — 프론트엔드 분기 기준

> v0.3 §6.5는 `BlockedResult.reason` 을 *"확장 가능한 정책 코드"* 로만 정의한다.
> 화면이 reason 별로 다르게 반응해야 하므로 **본 계약서가 값 목록을 관리한다.**
> 새 코드가 필요하면 §14 변경 절차를 따른다.

| `reason` | 발생 지점 | 프론트엔드 처리 |
| --- | --- | --- |
| `illegal_or_injection` | `check_input` block | 오류 배너 + 질문 재입력 |
| `need_clarification` | `check_input` warn | **재질문 입력창** → `extra.clarification` |
| `insufficient_info` | `question_analysis` 질문 분석 결과: 정보부족 | **재질문 입력창** → `extra.clarification` |
| `prohibited_item` | `check_regulation` block | 오류 배너 |
| `regulation_risk` | `check_regulation` warn 상한 초과 | **대안 문구 안내 + [다시 만들기]** |
| `sensitive_leak` | `check_output` block | 오류 배너 |
| `content_policy` | 개별 카피 슬롯 차단 | 해당 카드에만 오류 표시 |

> ⚠️ **`content_policy` 만 성격이 다르다.** 이건 최상위 `reason` 이 아니라
> v0.3 §6.2 **`ProposalError.reason`** (`rate_limit` · `content_policy` · `timeout` ·
> `unknown` · `parse_failed` 5종 enum)이다. 3안 중 일부만 막혔을 때
> 슬롯 안에 담기며, 이때 전체 `status` 는 여전히 `ok` 다(D-018 · 3안 고정).

### 12.4 재생성 예산과 모델 타임아웃

> v0.3 §6.6은 모델 호출 타임아웃을 **60초**로 고정한다.
> 본 계약서의 재생성 상한은 그 안에서만 유효하다.

```
법률 규제 재생성 2회  = 카피 생성 LLM 모델 API 호출 최대 3회
self_check 1회   = 파이프라인 생성 노드 재실행
+ 429 백오프(2→4→8초)
→ 합산이 60초를 넘으면 timeout 으로 전체 실패한다
```

> 그래프 진입 시 `state["deadline"]` 을 설정해 모든 `call_llm` 에 전달하고(D-144),
> 남은 예산이 부족하면 **재생성을 포기하고 현재 결과로 진행**한다.

---

## 13. ⚠️ 받는 쪽이 하면 안 되는 것(기본/컨설턴트/서비스 개발 담당자 대상)

```
① validation/ 내부 파일을 수정한다
   → 두 챗봇이 같은 파일을 쓴다. 한쪽이 고치면 다른 쪽이 깨진다
   → 필요하면 전민재 PM에게 요청

② action 값을 임의로 추가한다
   → "skip", "retry" 같은 값을 만들면 다른 챗봇과 규격이 어긋난다

③ message 를 직접 작성한다
   → 전민재 PM이 준 문구를 그대로 전달한다. 안내 톤이 팀마다 달라지면 안 된다

④ pass 가 아닌데 그냥 통과시킨다
   → 검증 함수를 붙인 의미가 사라진다. 스텁 기간에도 분기는 만들어 둔다

⑤ 크레딧 롤백을 LLM 모델 쪽에서 처리한다
   → 과금은 서비스 개발 담당 영역. LLM 모델은 판정 결과만 정확히 전달한다
```

---

## 14. 변경 절차

> 계약을 바꿔야 할 때 **코드보다 문서를 먼저** 고친다.

```
① 변경 필요 발견 → 스크럼 또는 팀 채널에 공유
② 전민재 PM이 본 문서(validation_contract.md) 수정
③ decisions.md 에 변경 이력 기록 (원래 줄은 지우지 않음)
④ tests/validation/test_contract.py 갱신
⑤ validation/ 구현 수정
⑥ 팀 채널 공지 → 두 챗봇 담당자가 노드 확인
```

> **④를 ⑤보다 먼저 하는 이유**: 테스트를 먼저 고치면 **구현이 검증 함수 계약을 어겼을 때 CI가 잡는다.**

---

## 15. 미확정 사항

| ID | 항목 | 현재 기본안 | Owner | Due |
| --- | --- | --- | --- | --- |
| V-01 | `check_input` `warn` 재질문 UX | **확정** — 그래프 종료 → `action="reask"`, `reason="need_clarification"` → 프론트엔드가 직전 요청을 유지한 채 `extra.clarification` 추가 + **새 Idempotency-Key** 로 재호출(v0.3 §6.5) | 전민재 PM | 8/18 종료 |
| V-02 | `check_output` `warn` 민감정보 마스킹 방식 | **확정(D-153)** — `check_output` 이 **`masked_text`** 를 반환하고 노드는 갈아끼우기만 한다(§5.1). 민감정보 마스킹 규칙은 `validation/` 관리 | 전민재 PM | 8/18 종료 |
| V-03 | `self_check` `reject` 재시도 횟수 | **확정** — **1회**, `self_check_retry_count` 로 재시도 카운터 분리(D-156)(법률 규제 재생성과 공유 금지) | 전민재 PM | 8/18 종료 |
| V-04 | `check_regulation` 2단 RAG 전환 | 1주차 키워드 → 2주차 RAG [SHOULD] | 전민재 PM | 8/19 |
| V-05 | `self_check` (B) LLM 모델 답변 사실성 검증 | SHOULD, OpenAI 예산 여유 시 | 전민재 PM | 8/21 |
| **V-06** | `alternative`·`law` 를 서비스 응답 별도 필드로 노출 여부 논의 | 기본안: **message 문장에 포함**(§5.2). 별도 필드는 v0.3 계약 변경 필요(D-046) | 전민재 PM | 8/18 |

---

## 참고 자료

### 서비스 개발 계약 문서
- 서비스 API/DB Contract v0.3 — [바로가기](https://app.notion.com/p/D1-API-DB-Contract-v0-3-3b9efe95f43b80938eaddafa09244fd3)

---

## 부록 A. 빠른 참조 — action 값 요약

```
check_input      : pass | warn(→reask) | block
check_regulation : pass | warn(→재생성 2회) | block
check_output     : pass | warn(→민감정보 마스킹) | block
self_check       : pass | warn(→로그만) | reject(→재시도 1회)

서비스 도달 시:
  status = "blocked"  → action = block | reask | warn   → 크레딧 롤백
  status = "error"    → self_check reject 재시도 실패    → 크레딧 롤백
  status = "ok"       → 정상                             → 차감 유지
```

## 부록 B. 참고 문서
- 요구사항 명세서 v10 (`v10_sw_req_spec.md`)
- 프로젝트 가이드 · 프로젝트 팁 (`project_tip.md`)
- 의사결정 로그 (`docs/decisions.md`) — D-011 · D-018 · D-019 · D-020
- 디렉토리 구조 (`docs/directory_structure.md`)
- **골든 데이터셋 기준 문서** (`docs/golden_dataset.md`) — `R-` 15문항이 본 계약을 검증
- 서비스 API/DB Contract v0.3 — §6.5 정책 검증 결과 · S-11 롤백
- 4개 담당자별 SDP 개발 계획서 (`docs/sdp_pm.md` / `sdp_service.md` / `sdp_basic.md` / `sdp_consult.md`)