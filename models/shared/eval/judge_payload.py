"""
models/shared/eval/judge_payload.py
— LLM Judge 에 넘길 응답을 '채점 대상 텍스트'만 남기도록 정제한다 (D-329)

★ 왜 필요한가
  기본 챗봇 성공 응답의 proposals 에는 image_b64(이미지 base64 원문)가 들어 있다.
  그대로 json.dumps() 해서 프롬프트에 넣으면
    · 1024 PNG 3안 = 약 175만 토큰 → context length exceeded 로 실패
    · 512 JPEG 3안 = 약 7만 토큰   → 실패하지 않고 조용히 예산을 태운다
  후자가 더 위험하다. 실패해서 드러난 게 오히려 다행이었다.

★ 이미지는 애초에 Judge 채점 대상이 아니다
  골든 데이터셋 rubric 4항목(요청_반영도·구체성·규제_안전성·채널_적합성)은
  전부 텍스트 카피에 대한 것이다. 이미지 품질은 eval_image.py 의 CLIP Score 소관이다.
  Judge 에게 base64 는 무작위 문자열이라 점수에 기여하지 못한다.

★ 서비스에 같은 선례가 있다
  backend/services/generation_service.py::serialize_model_result_for_storage 가
  DB 저장 시 image_b64 를 빼고 테스트로 고정해 두었다.
  같은 문제를 서비스는 풀었고 평가 코드만 안 풀었다.

★ 이중 방어 (D-330)
  ① 알려진 비텍스트 필드를 이름으로 제거 — 주 방어
  ② 남은 것 중 상한을 넘는 문자열·페이로드가 있으면 **예외** — 보험
     ★ 자르지 않는다. 자른 응답을 채점하면 '무엇을 채점했는지' 가 달라져
       재현성이 깨진다(기준 문서 §1.4). 멈추고 원인을 찾는 편이 낫다.
     ①만 두면 나중에 다른 큰 필드(raw_response·data URI 등)가 생겼을 때 또 터진다.
"""

from __future__ import annotations

import json

# 채점에 쓰이지 않는 비텍스트 필드 — 이름으로 제거한다
DROP_FIELDS = frozenset({
    "image_b64",
    "image_url",        # data URI 로 들어올 수 있다
    "thumbnail_b64",
    "raw_response",     # 디버그용 원본 — 채점 대상이 아니다
})

# 개별 문자열 상한. 광고 카피 한 편이 이걸 넘으면 정상 상황이 아니다.
MAX_FIELD_CHARS = 2_000
# 직렬화 후 전체 상한. rubric·질문까지 합쳐 프롬프트가 이 안에 들어와야 한다.
MAX_PAYLOAD_CHARS = 20_000


class JudgePayloadTooLarge(ValueError):
    """정제 후에도 페이로드가 상한을 넘었다 — 채점을 시도하지 않는다."""


def _strip(value, path: str, dropped: list[str]):
    """dict·list 를 재귀 순회하며 비텍스트 필드만 제거한다. 절단은 하지 않는다."""
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            here = f"{path}.{key}" if path else key
            if key in DROP_FIELDS:
                if item is not None:
                    dropped.append(here)
                continue
            out[key] = _strip(item, here, dropped)
        return out
    if isinstance(value, list):
        return [_strip(item, f"{path}[{i}]", dropped) for i, item in enumerate(value)]
    return value


def _oversized_fields(value, path: str, found: list[str]) -> list[str]:
    """상한을 넘는 문자열의 경로를 모은다."""
    if isinstance(value, dict):
        for key, item in value.items():
            _oversized_fields(item, f"{path}.{key}" if path else key, found)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            _oversized_fields(item, f"{path}[{i}]", found)
    elif isinstance(value, str) and len(value) > MAX_FIELD_CHARS:
        found.append(f"{path or '(root)'} ({len(value):,}자)")
    return found


def build_judge_payload(response: dict) -> tuple[dict, list[str]]:
    """Judge 프롬프트에 넣을 응답을 만든다.

    반환: (정제된 응답, 제거된 필드 경로 목록)
    Raises: JudgePayloadTooLarge — 정제 후에도 상한 초과
    """
    dropped: list[str] = []
    cleaned = _strip(response or {}, "", dropped)

    oversized = _oversized_fields(cleaned, "", [])
    if oversized:
        raise JudgePayloadTooLarge(
            f"채점 대상이 아닌 큰 필드가 남아 있다: {oversized}\n"
            f"(제거한 필드: {dropped or '없음'})\n"
            "→ DROP_FIELDS 에 추가하거나, 생성 노드가 왜 이렇게 긴 값을 내는지 확인한다."
        )

    serialized = json.dumps(cleaned, ensure_ascii=False, indent=2)
    if len(serialized) > MAX_PAYLOAD_CHARS:
        raise JudgePayloadTooLarge(
            f"정제 후에도 {len(serialized):,}자로 상한 {MAX_PAYLOAD_CHARS:,}자를 넘는다.\n"
            f"(제거한 필드: {dropped or '없음'} / 남은 최상위 키: {sorted(cleaned)})"
        )
    return cleaned, dropped


def dumps_for_judge(response: dict) -> tuple[str, list[str]]:
    """프롬프트에 바로 넣을 문자열까지 만든다."""
    cleaned, dropped = build_judge_payload(response)
    return json.dumps(cleaned, ensure_ascii=False, indent=2), dropped


def strip_for_report(response: dict) -> tuple[dict, list[str]]:
    """결과 파일에 보존할 응답 — 이미지만 빼고 상한 검사는 하지 않는다 (D-331).

    기준 문서 §10.4 DoD ③ 은 '문항별 원본 응답 보존' 을 요구하지만,
    이미지까지 넣으면 리포트 파일이 수 MB 가 되어 Git 저장소가 부푼다.
    서비스가 DB 저장 시 image_b64 를 빼는 것과 같은 판단이다.
    """
    dropped: list[str] = []
    return _strip(response or {}, "", dropped), dropped
