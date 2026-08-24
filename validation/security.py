"""
validation/security.py
보안1 = check_input  (LLM 호출 전 · 막는 검증)
보안2 = check_output (응답 직전 · 고쳐서 내보내는 검증)

★ 두 함수 모두 LLM 을 호출하지 않는다.
  check_input 이 LLM 앞에 있는 이유가 "여기서 막으면 호출 0회·비용 0원"인데,
  막으려고 LLM 을 부르면 설계가 무너진다.
"""

from __future__ import annotations

from . import config as C
from . import patterns as P


# ── 반환 헬퍼 ────────────────────────────────────────────────────────────────
def _input_result(action: str, message: str = "") -> dict:
    return {"action": action, "message": message}


def _output_result(action: str, message: str, masked_text: str) -> dict:
    return {"action": action, "message": message, "masked_text": masked_text}


# ═════════════════════════════════════════════════════════════════════════════
# check_input — 보안1
# ═════════════════════════════════════════════════════════════════════════════
_MSG_ILLEGAL = (
    "요청하신 내용은 법령상 광고가 제한되는 품목이라 도와드리기 어려워요. "
    "판매 중인 다른 메뉴나 상품으로 다시 요청해 주세요."
)
_MSG_INJECTION = (
    "요청을 처리할 수 없어요. 광고 문구나 이미지 제작과 관련된 내용으로 다시 입력해 주세요."
)
_MSG_EMPTY = "어떤 광고를 만들고 싶으신지 한 문장으로 알려주세요. (예: 여름 신메뉴 홍보 문구)"
_MSG_TOO_LONG = (
    f"입력이 너무 길어요. {C.MAX_INPUT_CHARS}자 이내로 핵심만 정리해서 다시 보내주세요."
)


def check_input(text: str) -> dict:
    """사용자 질문 검증 — 불법 품목·프롬프트 인젝션을 차단한다.

    반환: {"action": "pass"|"warn"|"block", "message": str}

    ⚠️ warn 은 매우 좁게 쓴다 (D-273).
       "정보가 부족한가?" 는 question_analysis 노드의 일이다. 여기서 warn 을
       남발하면 reask 왕복이 늘고 사용자 크레딧이 계속 소모된다(계약서 §7).
       여기서의 warn 은 "질문이라고 볼 수 없는 입력"만 해당한다.
    """
    raw = text or ""
    stripped = raw.strip()

    # ── 0) 형식 ──────────────────────────────────────────────────────────────
    if len(stripped) < C.MIN_INPUT_CHARS:
        return _input_result("warn", _MSG_EMPTY)
    if len(stripped) > C.MAX_INPUT_CHARS:
        return _input_result("warn", _MSG_TOO_LONG)
    # 자모·기호만 있는 입력 ("ㅋㅋㅋ", "ㅇㅇ", "???")
    if not any(c.isalnum() and not ("\u3130" <= c <= "\u318f") for c in stripped):
        return _input_result("warn", _MSG_EMPTY)

    low = P.normalize(stripped)
    tight = P.squeeze(stripped)

    # ── 1) 프롬프트 인젝션 ───────────────────────────────────────────────────
    # ★ 원문과 압축본 **양쪽**에서 검사한다.
    #   tight(squeeze)만 쓰면 "이 전 지 시 무 시" 같은 공백 삽입은 잡지만,
    #   "<|im_start|>" 처럼 구분자 자체가 패턴인 경우 squeeze 가 | 를 지워 놓쳐버린다.
    #   반대로 low 만 쓰면 공백 삽입 회피를 놓친다 — 둘 다 봐야 한다.
    for _name, pat in P.INJECTION_PATTERNS:
        if pat.search(tight) or pat.search(low):
            return _input_result("block", _MSG_INJECTION)

    # ── 2) 불법 품목 A: 단독 차단 어휘 ───────────────────────────────────────
    # 사전 항목이 공백 없는 형태라 압축본에서도 확인한다.
    for kw in P.HARD_ILLEGAL:
        if kw in low or kw in tight:
            return _input_result("block", _MSG_ILLEGAL)

    # ── 3) 불법 품목 B: 품목 + 거래동사 공기 시에만 차단 ────────────────────
    #    "마약 김밥 홍보 문구" 는 통과, "마약 판매 광고" 는 차단.
    #    ★ 과잉 차단 가드(골든 R-011~R-015)가 지켜지는 지점이다.
    # ★ 사전 항목이 '처방전없이' 처럼 공백 없는 형태라 압축본도 함께 본다.
    #   "처방전 없이 살 수 있는" 은 normalize 로는 안 걸리고 squeeze 로만 걸린다.
    item_hit = next((k for k in P.ILLEGAL_ITEMS if k in low or k in tight), None)
    if item_hit:
        safe = any(s in low or s in tight for s in P.ITEM_SAFE_CONTEXT)
        trade = any(v in low or v in tight for v in P.TRADE_VERBS)
        # '홍보/광고'는 거래동사에 들어있지만, 음식 문맥이면 정상 요청이다.
        if trade and not safe:
            return _input_result("block", _MSG_ILLEGAL)

    return _input_result("pass", "")


# ═════════════════════════════════════════════════════════════════════════════
# check_output — 보안2
# ═════════════════════════════════════════════════════════════════════════════
_MSG_LEAK = "내부 설정 정보가 포함되어 응답을 반환하지 않았습니다. 다시 시도해 주세요."


def _mask_digits(s: str, keep_head: int = 3, keep_tail: int = 0) -> str:
    tail = s[len(s) - keep_tail:] if keep_tail else ""
    mid = s[keep_head:len(s) - keep_tail] if keep_tail else s[keep_head:]
    return s[:keep_head] + "".join("*" if c.isdigit() else c for c in mid) + tail


def check_output(text: str) -> dict:
    """최종 응답 텍스트 검증 — 민감정보를 마스킹하고, 내부 정보 누출은 차단한다.

    반환: {"action": ..., "message": str, "masked_text": str}
      · pass  → masked_text 는 입력 원문 그대로
      · warn  → masked_text 는 마스킹본 (노드가 이 값으로 갈아끼운다)
      · block → masked_text 는 ""

    ★ 스팬 선점 방식으로 처리한다 (D-274)
      정규식을 순서대로 sub() 하면 "010-1234-5678"이 계좌번호 정규식에 먼저
      잡혀 전화번호 규칙이 아예 실행되지 않는다. 구체적인 패턴이 먼저 스팬을
      선점하게 해야 판정이 결정적(deterministic)이 된다.

    ★ 전화번호·이메일을 무조건 가리지 않는다
      "문의 010-1234-5678" 은 소상공인 광고의 정상 구성요소다.
      식품표시광고법 제7조도 광고에 제품명·업소명을 넣도록 요구한다.
      → 광고 CTA 문맥(문의·예약·주문…)이 함께 있으면 사업자 연락처로 보고 통과시킨다.
    """
    original = text or ""
    if not original.strip():
        return _output_result("pass", "", original)

    # ── 1) 크리덴셜·시스템 프롬프트 누출 → block ────────────────────────────
    #    마스킹으로 안전을 보장할 수 없는 유일한 부류다. 부분 노출도 사고다.
    for _name, pat in P.LEAK_PATTERNS:
        if pat.search(original):
            return _output_result("block", _MSG_LEAK, "")

    keep_contact = P.has_cta_context(original)

    def _rrn(m: str) -> str | None:
        return "******-*******" if P.rrn_date_ok(m[:6]) else None

    def _card(m: str) -> str | None:
        if not P.luhn_ok(m):
            return None
        return "****-****-****-" + "".join(c for c in m if c.isdigit())[-4:]

    def _phone(m: str) -> str | None:
        if keep_contact:
            return m                       # 사업자 연락처 — 원문 유지
        head = m[:3]
        return f"{head}-****-****"

    def _tel(m: str) -> str | None:
        if keep_contact:
            return m
        return _mask_digits(m, keep_head=m.find("-") + 1 if "-" in m else 3)

    def _email(m: str) -> str | None:
        if keep_contact:
            return m
        local, _, domain = m.partition("@")
        return f"{local[:2]}***@{domain}"

    # 순서 = 우선순위. 앞선 규칙이 선점한 구간은 뒤 규칙이 건드리지 않는다.
    spec: list[tuple[str, object, object]] = [
        ("주민등록번호", P.RRN_RE, _rrn),
        ("카드번호", P.CARD_RE, _card),
        ("이메일", P.EMAIL_RE, _email),
        ("사업자번호", P.BIZNO_RE, lambda m: m),      # 안전 스팬: 선점만, 마스킹 없음
        ("연락처", P.PHONE_RE, _phone),
        ("연락처", P.TEL_RE, _tel),
        ("계좌번호", P.ACCOUNT_RE, lambda m: _mask_digits(m, keep_head=3)),
    ]

    claimed: list[tuple[int, int, str, str]] = []   # (start, end, kind, replacement)
    taken: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        return any(a < e and s_ < b for s_, e in taken)

    for kind, pattern, repl in spec:
        for m in pattern.finditer(original):
            if overlaps(m.start(), m.end()):
                continue
            new = repl(m.group(0))
            if new is None:                 # 체크섬·날짜 검증 탈락 → 민감정보 아님
                continue
            taken.append((m.start(), m.end()))
            claimed.append((m.start(), m.end(), kind, new))

    changed = [c for c in claimed if c[3] != original[c[0]:c[1]]]
    if not changed:
        return _output_result("pass", "", original)

    out, cursor = [], 0
    for start, end, _kind, new in sorted(claimed):
        out.append(original[cursor:start])
        out.append(new)
        cursor = end
    out.append(original[cursor:])
    masked = "".join(out)

    kinds = " · ".join(dict.fromkeys(c[2] for c in changed))
    return _output_result(
        "warn",
        f"{kinds}로 보이는 정보를 가렸습니다. 필요하면 직접 수정해 주세요.",
        masked,
    )
