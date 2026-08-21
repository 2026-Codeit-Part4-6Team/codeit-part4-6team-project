"""
validation/patterns.py
보안1(check_input)·보안2(check_output) 이 쓰는 패턴 사전.

★ 왜 별도 파일인가
  두 함수가 같은 사전을 본다. security.py 안에 두면 "보안2에도 추가해야 하나?"
  라는 질문이 매번 생긴다. 사전은 하나, 함수는 둘이다.

★ 규제(check_regulation) 트리거는 여기 없다
  규제 1단 트리거는 shared_data/legal_kb.md 에서 자동 생성된다 (D-272).
  키워드 사전과 법률 KB 가 따로 놀면, 1단에서 걸렸는데 2단이 검색할 조문이
  없는 사고가 난다.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

# ═════════════════════════════════════════════════════════════════════════════
# 0. 정규화 — 우회 입력 방어
# ═════════════════════════════════════════════════════════════════════════════
_ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff\u2060]")
_SEPARATORS = re.compile(r"[\s\-_.·•*~/\\|]+")


def normalize(text: str) -> str:
    """대소문자·전각/반각·유니코드 합자를 통일한다 (일반 매칭용)."""
    return unicodedata.normalize("NFKC", _ZERO_WIDTH.sub("", text or "")).lower()


def squeeze(text: str) -> str:
    """구분자를 전부 제거한다 (인젝션 우회 방어 전용).

    "이 전 지 시 무 시" · "i-g-n-o-r-e" 같은 회피를 잡는다.
    ⚠️ 일반 키워드 매칭에는 쓰지 않는다 — 오탐이 폭발한다.
    """
    return _SEPARATORS.sub("", normalize(text))


# ═════════════════════════════════════════════════════════════════════════════
# 1. 불법 품목 (check_input → block)
# ═════════════════════════════════════════════════════════════════════════════
# [A] 단독 등장만으로 차단. 정상 광고 문맥에서 나올 수 없는 어휘만 넣는다.
HARD_ILLEGAL = [
    "필로폰", "히로뽕", "메스암페타민", "메트암페타민",
    "코카인", "헤로인", "케타민", "엑스터시", "lsd", "펜타닐",
    "대마초", "떨액", "물뽕", "졸피뎀",
    "아동성착취", "아청물", "성매매알선",
    "사제총기", "사제총", "사제폭탄", "폭발물제조",
    "장기매매", "청부살인",
    # ── 도박·성매매·위조품: 소상공인 광고 문맥에서 정당하게 등장할 수 없다 ──
    "사설토토", "바카라", "홀덤펍", "슬롯머신", "환전가능",
    "조건만남", "성매매", "유흥접대", "접대부",
    "대포통장", "대포폰", "명의대여",
    "레플리카", "이미테이션", "미러급", "s급짝퉁",
]

# [B] 품목 어휘 — 단독으로는 차단하지 않는다.
#     "마약 김밥"(메뉴명) 과 "마약 팝니다"(불법거래) 를 구분해야 하기 때문이다.
#     → 아래 TRADE_VERBS 와 함께 등장할 때만 block. (D-273 · 골든 R-011~015 가드)
ILLEGAL_ITEMS = [
    "마약", "대마", "케타민", "향정신성", "마약류",
    "총기", "권총", "실탄", "도검",
    "도박", "토토", "카지노", "베팅", "배팅",
    "성인용품",
    "짝퉁", "가품", "위조품", "모조품",
    "전문의약품", "처방전없이", "스테로이드", "발기부전치료제",
    "개인정보db",
]

TRADE_VERBS = [
    "판매", "팝니다", "팔아", "구매", "삽니다", "구합니다",
    "유통", "거래", "배송", "직거래", "공급", "도매", "택배",
    "입금", "계좌", "무료체험", "홍보", "광고",
    "가입", "이벤트", "충전", "환전", "배당", "먹튀",
    "문의", "상담", "오픈채팅", "텔레", "디엠",
]

# 불법 품목이지만 "일반 명사로도 쓰이는" 경우의 정당 문맥.
# 이게 걸리면 [B] 매칭을 무효화한다.
ITEM_SAFE_CONTEXT = [
    "김밥", "떡볶이", "치킨", "토스트", "옥수수", "라면", "국수", "닭발",
    "소스", "양념", "레시피", "메뉴", "맛집", "분식", "포장",
    "금지", "예방", "근절", "신고", "단속", "캠페인", "주의",
]

# ═════════════════════════════════════════════════════════════════════════════
# 2. 프롬프트 인젝션 (check_input → block)
#    §6.5 방침: "대표 패턴 5~10개"로 범위를 한정한다. 완벽 방어는 목표가 아니다.
# ═════════════════════════════════════════════════════════════════════════════
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("지시_무시", re.compile(
        r"(이전|위의|앞의|모든|기존)?(지시|명령|규칙|프롬프트|instruction)s?(를|을)?(무시|잊어|삭제|해제)"
        r"|ignorepreviousinstruction|disregard(all|previous|above)")),
    ("프롬프트_탈취", re.compile(
        r"(시스템|system)?(프롬프트|prompt|지침|설정|규칙)(을|를)?(알려|보여|출력|공개|말해|repeat|reveal|print|show)"
        r"|revealyour(system)?prompt|whatareyourinstructions")),
    ("역할_재정의", re.compile(
        r"(너는|당신은|you are)(이제|now)?(더이상)?.{0,12}(아니|아냐|not)"
        r"|(개발자|디버그|관리자|admin|developer|god)모드"
        r"|actas(dan|jailbreak)|dan모드|무제한모드")),
    ("제약_해제", re.compile(
        r"(제한|필터|검열|규제|안전장치|가드레일|guardrail|filter)(없이|해제|끄고|off|bypass)"
        r"|jailbreak|withoutanyrestriction|nolimits")),
    ("구분자_위조", re.compile(
        r"<\|im_(start|end)\|>|\[/?(system|assistant|inst)\]|###system|<<sys>>|```system")),
    ("출력_탈취", re.compile(
        r"(다음|아래)(문장|텍스트|내용)(을|를)?(그대로|정확히)?(출력|반복|복사)"
        r"|repeataftermeexactly")),
]

# ═════════════════════════════════════════════════════════════════════════════
# 3. 민감정보 (check_output)
#    ★ 티어를 나눈다. 전부 같은 등급으로 다루면 광고 서비스가 망가진다.
#      TIER_BLOCK : 유출 자체가 사고 → 텍스트 폐기
#      TIER_MASK  : 가리고 계속 진행
#      TIER_CTA   : 광고 CTA 문맥이면 정상 (사업자 연락처) → pass  (D-274)
# ═════════════════════════════════════════════════════════════════════════════

# 광고 카피에 연락처가 들어가는 정당한 신호.
# 식품표시광고법 제7조는 광고에 제품명·업소명을 넣도록 요구한다 —
# 연락처를 무조건 가리면 그 광고는 쓸 수가 없다.
CTA_CONTEXT = [
    "문의", "예약", "주문", "연락", "상담", "전화", "call", "톡",
    "오시는길", "오시는 길", "찾아오시는", "배달", "포장", "픽업",
    "영업시간", "매장", "가게", "지점", "본점",
]

# 시스템 프롬프트/크리덴셜 누출 — 무조건 block
LEAK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("api_key", re.compile(r"\b(sk|rk)-[A-Za-z0-9_\-]{16,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("bearer", re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{20,}\b", re.IGNORECASE)),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("system_prompt", re.compile(
        r"(당신은|너는)\s*(소상공인|광고|카피).{0,30}(어시스턴트|도우미|전문가)입니다"
        r"|SYSTEM_PROMPT|system\s*:\s*you are", re.IGNORECASE)),
    ("db_url", re.compile(r"\b(postgres|postgresql|mysql|mongodb)(\+\w+)?://\S+", re.IGNORECASE)),
]

RRN_RE = re.compile(r"\b(\d{6})[-\s]?([1-8]\d{6})\b")            # 주민등록번호
CARD_RE = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")             # 카드번호
# 사업자등록번호(3-2-5)·통신판매업 신고번호는 광고에 정상적으로 들어간다.
# 계좌번호 정규식보다 먼저 '안전 스팬'으로 선점해 오탐을 막는다.
BIZNO_RE = re.compile(r"\b\d{3}-\d{2}-\d{5}\b")
ACCOUNT_RE = re.compile(r"\b\d{2,6}-\d{2,6}-\d{2,7}\b")      # 계좌번호(은행 통용형)
PHONE_RE = re.compile(r"\b(01[016789])[-\s.]?(\d{3,4})[-\s.]?(\d{4})\b")
TEL_RE = re.compile(r"\b(0(?:2|[3-6][1-5]))[-\s.]?(\d{3,4})[-\s.]?(\d{4})\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b")


def luhn_ok(digits: str) -> bool:
    """카드번호 체크섬. 정규식만 쓰면 '2024-1234-5678-9012' 같은 숫자열도
    전부 카드로 오인한다 — 과잉 차단률(FPR)이 여기서 갈린다."""
    nums = [int(c) for c in digits if c.isdigit()]
    if len(nums) != 16:
        return False
    total, parity = 0, len(nums) % 2
    for i, n in enumerate(nums):
        if i % 2 == parity:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def rrn_date_ok(front: str) -> bool:
    """주민등록번호 앞 6자리가 실제 날짜인지 확인한다.
    '250101' 은 날짜지만 사업자번호 조각 '123456' 은 아니다."""
    try:
        mm, dd = int(front[2:4]), int(front[4:6])
        if not (1 <= mm <= 12 and 1 <= dd <= 31):
            return False
        date(2000, mm, min(dd, 28))
        return True
    except ValueError:
        return False


def has_cta_context(text: str) -> bool:
    """이 텍스트가 '사업자 연락처를 노출하는 광고 문구'인가."""
    low = normalize(text)
    return any(k in low for k in CTA_CONTEXT)
