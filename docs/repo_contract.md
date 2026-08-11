# 조회 함수 계약서 (cache/)

> 컨설턴트 챗봇 모델 개발 담당자가 관리하는 데이터 계층(1·2층) 조회 함수. 기본 챗봇 담당자도 그대로 가져다 쓴다.
> 상태: D1 mock 스텁 단계. 내부 구현(Cache-Aside)은 이후 단계에서 채워지지만 시그니처·반환 필드는 이 문서 기준으로 고정한다.

## `cache.market_repo.get_market`

```python
def get_market(
    lat: float, lng: float, radius: int = 500, industry: str | None = None
) -> dict | None:
    ...
```

- `industry`: 호출하는 쪽(전략 노드)이 API 계약(§6.2)의 `store.type`을 그대로 전달한다.
  `same_industry_count`·`nearest_distance_m`은 이 값을 기준으로 계산된다.
  **`industry`가 없으면** 비교 기준이 없으므로 두 필드 모두 `None`을 반환한다 — "경쟁사 0개"라는 확정값과
  "모름"을 구분해야 잘못된 마케팅 근거로 이어지지 않는다.
  **`industry`는 있지만 동일 업종 매장이 0개면** `same_industry_count=0`, `nearest_distance_m=None`을 반환한다
  (매장 수는 확정할 수 있지만 거리는 존재하지 않음).

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `total_count` | int | 반경 내 전체 매장 수 |
| `same_industry_count` | int \| None | `industry`와 같은 업종 매장 수. `industry` 없으면 None(모름) |
| `nearest_distance_m` | int \| None | 최근접 동일업종(= `industry`) 매장까지의 거리(m). `industry` 없거나 동일 업종이 0개면 None |
| `industry_breakdown` | dict[str, int] | 업종명 → 매장 수 (예: `{"카페": 12, "편의점": 5}`). 이 형식이 최종 계약이며, 외부 API 응답 형식이 다르면 `market_repo` 내부에서 이 형식으로 변환해 반환한다 |

- 실패 시 `None`을 반환한다(현재 mock 단계는 항상 dict를 반환).
- 좌표는 소수 3자리로 반올림돼 캐시 키로 쓰일 예정(D2에서 구현).

## `cache.trend_repo.get_trend`

```python
def get_trend(keyword: str, industry: str | None = None) -> dict | None:
    ...
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `keyword` | str | 조회한 검색어 |
| `direction` | str | `"상승"` / `"하락"` / `"유지"` |
| `related` | list[str] | 연관 검색어 |
| `weather` | dict \| None | 날씨 정보(선택). 있으면 `{"temp": float, "sky": str}` 형태 — 이 형식이 최종 계약이며, 외부 API 응답 형식이 다르면 `trend_repo` 내부에서 이 형식으로 변환해 반환한다 |

- 실패 시 `None`을 반환한다(현재 mock 단계는 항상 dict를 반환).

## 참고

- 두 함수 모두 캐시든 API 호출이든 시그니처는 동일하다. 호출하는 쪽은 내부 동작을 알 필요가 없다.
- 상세 배경: `docs/consult_sdp.md` §2.4, §2.7
