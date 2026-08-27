# 검증 함수 평가 보고서 초안 (Validation Report) v1.0

- **작성자**: 전민재 PM
- **작성일**: 2026-08-27
- **파일 위치**: `docs/validation_report.md` (단일 소스)
- **구현 위치**: `validation/` (전민재 PM 관리 — 두 챗봇 담당자는 **import만**)
- **연관 문서**: `docs/golden_dataset.md` · `docs/decisions.md` · 서비스 API/DB Contract v0.4

---

## 📊 1차 성능 평가 결과

### refusal 튜닝 전후 비교

| 지표 | 튜닝 전 | 튜닝 후 | 변화 |
| --- | --- | --- | --- |
| block_recall | 100.0% | 100.0% | 0.0%p |
| warn_recall | 1.0 | 1.0 | 0.0 |
| over_block_rate | 8.33% | 8.33% | 0.0%p |
| alternative_rate | 100.0% | 100.0% | 0.0%p |
| **alternative_validity** | 0.9 | 1.0 | **+0.1** |
| safety_score | 0.99 | 0.99 | 0.0 |
| macro_f1 | 0.99 | 0.99 | 0.0 |
| accuracy | 0.99 | 0.99 | 0.0 |
| context_recall | 1.0 | 1.0 | 0.0 |
| context_precision | 0.39 | 0.39 | 0.0 |
| faithfulness | 1.0 | 1.0 | 0.0 |
| ragas_score | 0.65 | 0.65 | 0.0 |
| mrr | 0.98 | 0.98 | 0.0 |
| hit_at_1 | 0.97 | 0.97 | 0.0 |
| ndcg_at_3 | 0.88 | 0.88 | 0.0 |
| kb_coverage_rate | 0.94 | 0.94 | 0.0 |
| latency_p50_s | 0.0 | 0.01 | +0.01 |
| latency_p95_s | 0.02 | 1.36 | +1.34 |

```
측정 조건
- generation_model      : gpt-5.4-mini  (전·후 동일)
- judge_model           : gpt-5.4-mini  (전·후 동일)
- dataset_version       : refusal-v2-26ba36ab  (전·후 동일)
- fixture_version       : legal_kb-9b24351781436ae2  (전·후 동일)
- trend_fixture_version : n/a  (전·후 동일)
- retrieval_mode        : vector  (전: local → 후: vector)
- rag_enabled           : True  (전: False → 후: True)
- 바꾼 것               : 최종: 견고성 포함
```

```
성능 수치 — 과잉 차단률 8.3%로 확정
■ 판정 정확도 (67문항, 동일 조건 5회 측정)
   차단 정확도    100.0%     — 5회 모두 동일. 누락 0건
   과잉 차단률      8.3%     — 5회 중 3회 (0.0% 2회)
   Macro-F1       0.985
   안전 점수       0.995

■ 견고성
   불변성         98.0%     — 244건 변형 중 5건
                            (공백 삽입 우회 방어: 86.1% → 98.0%)

■ 검색 품질 (31문항) — 5회 모두 동일
   context_recall  1.000    MRR 0.984   Hit@1 0.968
   faithfulness    1.000    — 법 조항 환각 0건

■ 대안 품질 — 5회 모두 동일
   대안 제시율     100.0%    대안 유효성 100.0%

■ 커버리지
   legal_kb  도달 가능 34조문 100% (전체 36 중 94.4%)
```

---

## 참고 
- 1차 성능 평가 결과

<img width="960" height="1032" alt="image" src="https://github.com/user-attachments/assets/7cf906d0-8ccf-49c5-965b-a810c653bb2c" />

<img width="960" height="1032" alt="image" src="https://github.com/user-attachments/assets/02ebfd41-fad6-4df3-a907-dc235c3ca101" />

<img width="960" height="1032" alt="image" src="https://github.com/user-attachments/assets/7a551956-dd7a-44d2-b334-b209ec40c47e" />

- PR 리뷰: [#196](https://github.com/2026-Codeit-Part4-6Team/codeit-part4-6team-project/pull/196)