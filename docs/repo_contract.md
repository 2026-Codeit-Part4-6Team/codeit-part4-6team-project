# 조회 함수 계약서 (cache/)

> 컨설턴트 챗봇 모델 개발 담당자가 관리하는 데이터 계층(1·2층) 조회 함수. 기본 챗봇 담당자도 그대로 가져다 쓴다.
> 상태(2026-08-14 기준): `get_market()`·`get_trend()` 모두 실제 Cache-Aside 구현 완료(D2·D5). 시그니처·반환 필드는 두 함수 모두 이 문서 기준으로 고정돼 있다.

## `cache.market_repo.get_market` (실제 구현, D2 완료)

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

> ⚠️ **골든 문항에 이 예시 수치(12곳·43곳·55m)를 그대로 복사하지 않는다(D-231, D-218).**
> 이 값이 프롬프트 few-shot 예시와 겹쳐서, 골든 문항의 `market_fixture`에 그대로 쓰면
> LLM이 실제 데이터를 안 읽고 예시를 베껴도 환각 검증을 통과하게 된다.

**예시 응답 — `industry` 지정 시** (`get_market(37.4980, 127.0276, industry="카페")`)

```json
{
  "total_count": 43,
  "same_industry_count": 12,
  "nearest_distance_m": 55,
  "industry_breakdown": {"카페": 12, "편의점": 5}
}
```

**예시 응답 — `industry` 없을 시** (`get_market(37.4980, 127.0276)`)

```json
{
  "total_count": 43,
  "same_industry_count": null,
  "nearest_distance_m": null,
  "industry_breakdown": {"카페": 12, "편의점": 5}
}
```

- 실패 시 `None`을 반환한다.
- 좌표는 소수 3자리로 반올림돼 캐시 키로 쓰인다(약 100m 단위로 캐시 공유, TTL 7일).

## `cache.trend_repo.get_trend` (실제 구현, D5 완료)

```python
def get_trend(keyword: str) -> dict | None:
    ...
```

> ⚠️ **`industry` 파라미터는 제거됐다.** 트렌드 조회에 쓰는 두 API(NAVER API HUB
> 검색어 트렌드, 검색광고 연관 검색어)가 애초에 업종 개념을 받지 않고,
> `get_trend()`는 가공까지 끝난 최종 결과를 통째로 캐싱해 같은 검색어를
> 업종별로 나눠 캐싱할 이유도 없었다(D-188). 컨설턴트 쪽 호출부(`trend_for_consult.py`)는
> 애초에 `industry`를 넘기지 않아 영향이 없다. 기본 챗봇 호출부(`trend_for_copy.py`)는
> 아직 `industry=` 키워드 인자로 호출 중이라 별도 PR로 정리가 필요하다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `keyword` | str | 조회한 검색어 |
| `direction` | str | `"상승"` / `"하락"` / `"유지"` |
| `related` | list[str] | 연관 검색어 |
| `weather` | dict \| None | 날씨 정보(선택). 있으면 `{"temp": float, "sky": str}` 형태 — 이 형식이 최종 계약이며, 외부 API 응답 형식이 다르면 `trend_repo` 내부에서 이 형식으로 변환해 반환한다 |

**예시 응답** (`get_trend("아이스아메리카노")`)

```json
{
  "keyword": "아이스아메리카노",
  "direction": "상승",
  "related": ["여름음료", "냉커피"],
  "weather": null
}
```

> `weather`는 현재 미구현이다(날씨 API 미연동) — `get_trend()`는 항상 `null`을 반환한다.

- 실패 시 `None`을 반환한다. 좌표 없이 검색어(`keyword`)만으로 캐시 키를 쓰며(공백 제거 정규화), TTL 7일.

## 참고

- 두 함수 모두 캐시든 API 호출이든 시그니처는 동일하다. 호출하는 쪽은 내부 동작을 알 필요가 없다.
- 상세 배경: `docs/sdp_consult.md` §2.4, §2.7
