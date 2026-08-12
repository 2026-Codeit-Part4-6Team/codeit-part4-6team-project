## 7. 프로젝트 디렉토리 구조 (팀 통합본)

> **디렉토리 구조 변경 사항**: `model_basic/`·`model_consult/` → **`models/{shared,basic,consult}/`** 로 재편.
> 두 챗봇에 중복되던 `llm.py` 등을 `models/shared/`(전민재 PM 관리)로 통합했다. (D-030, D-031)

> **통합 원칙 6가지**
> 1. **4개 SDP의 모든 경로·주석을 보존한다** — 하나도 삭제하지 않음
> 2. **1인칭("내 담당")은 전부 역할명으로 치환** — 통합 시 누구인지 알 수 없게 되므로
> 3. **같은 경로에 여러 담당자 파일이 있으면 합친다** — `tests/`·`docs/`가 해당
> 4. **문서는 루트 `docs/` 한 곳으로 모은다** — 3곳에 흩어져 있으면 못 찾음
> 5. **완전히 동일한 코드만 `models/shared/`로 올린다** — 하는 일이 다르면 분리 유지
> 6. **`models/`는 `backend/`의 형제다** — 하위로 넣지 않음(배포 단위·Mock 전략·관리자 경계 유지)

### 7.1 관리자 한눈에 보기

| 디렉토리 | 관리자 | 다른 담당자 |
| --- | --- | --- |
| `validation/` | **전민재 PM** | import만 (수정 금지) |
| `models/shared/` | **전민재 PM** | import만 (수정 금지) |
| `cache/` | **컨설턴트 챗봇 담당** | import만 (수정 금지) |
| `shared_data/` | **전민재 PM + 컨설턴트 담당** | 읽기만 |
| `backend/` · `frontend/` | **서비스 개발 담당** | — |
| `models/basic/` | **기본 챗봇(게시물 생성) 담당** | — |
| `models/consult/` | **컨설턴트 챗봇 담당** | — |
| `scripts/` (루트) | **전민재 PM** | — |
| `tests/` (루트) | **서비스 개발 담당 + 전민재 PM** | 파일명으로 구분 |
| `docs/` (루트) | **전원 공용** | 파일명으로 구분 |

> ⚠️ **한 파일에는 관리자 한 명.** 남의 디렉토리 파일은 **import만** 하고 내부를 수정하지 않는다.
> 수정이 필요하면 관리자에게 요청한다. → 머지 충돌 방지

---

### 7.2 전체 구조

```
(예시)
sales-booster/
│
├── validation/                       # ★★ 전민재 PM 관리 — 두 챗봇 담당자는 import만
│   ├── keywords.py                   # banned_keywords 로딩·대조 (공통 유틸)
│   ├── patterns.py                   # 인젝션 대표 패턴 · RISKY_HINTS(1단 필터)
│   ├── security.py                   # check_input(보안1) + check_output(보안2)
│   │                                 #   ※ 둘 다 순수 보안이라 한 파일로 관리
│   │                                 #   ★ D1에 두 함수 모두 pass 스텁으로 먼저 커밋
│   │                                 #     check_input  → D2에 내용 채움
│   │                                 #     check_output → D5에 내용 채움
│   ├── regulation.py                 # ★ check_regulation — 1단 키워드 + 2단 RAG
│   │                                 #   ★ D1 스텁 → D4 구현
│   ├── self_check.py                 # self_check (품질 검사 — 보안 아님)
│   │                                 #   ★ D1 스텁 → D5 구현
│   ├── legal_retriever.py            # legal_kb FAISS 검색 래퍼
│   └── data/
│       └── banned_keywords.csv       # 규제 키워드 사전 (전민재 PM 작성)
│
├── cache/                            # ★★ 컨설턴트 챗봇 담당 관리 (1·2층) — 두 챗봇 공용
│   ├── models.py                     # MarketCache·TrendCache·ReviewCache ORM
│   │                                 #   ※ 테이블 DDL은 서비스 개발 담당자가 생성
│   ├── market_repo.py                # ★ Cache-Aside · TTL 7일 · get_market()   [MUST]
│   │                                 #   market_cache 적재 + get_market() 조회
│   ├── trend_repo.py                 # ★ Cache-Aside · TTL 7일 · get_trend()    [SHOULD]
│   │                                 #   트렌드 API 호출 + get_trend() 조회
│   ├── review_repo.py                # 사전 배치 전용 · TTL 30일 · get_review()  [COULD]
│   │                                 #   review_cache 적재 + 조회
│   │                                 #   ※ 기본 챗봇 담당자는 미사용
│   └── ttl.py                        # TTL 만료 판정 공통 유틸
│                                     #   ★ D1에 mock 반환 스텁으로 먼저 커밋
│
├── shared_data/                      # ★ 전민재 PM/컨설턴트 담당자가 채우는 데이터 자산
│   │                                 #   기본 챗봇 담당자는 읽기만
│   ├── legal_kb.md                   # ★ 규제 RAG 원본
│   │                                 #   (전민재 PM 작성·1차 검토, 2차 검토 - 다른 담당자)
│   ├── legal_kb.json                 # 스크립트가 생성 (gitignore 가능)
│   ├── legal_index/                  # FAISS 인덱스 파일
│   ├── golden_dataset.json           # 골든 데이터셋 55문항
│   │                                 #   (기준=전민재 PM, 문항=팀 분담)
│   │                                 #   ※ 컨설팅 문항은 컨설턴트 챗봇 담당자가 작성
│   └── benchmark_kb.json             # 업종 벤치마크 KB 데이터
│                                     #   (전민재 PM 또는 컨설턴트 챗봇 담당자가 작성)
│
├── backend/                          # ★★ 서비스 개발 담당 관리
│   ├── main.py                       # FastAPI 앱 조립 · 라우터 등록 · CORS
│   ├── config.py                     # .env 로딩(설정값·상수)
│   ├── database.py                   # SQLAlchemy engine/session, get_db()
│   ├── models.py                     # ORM 모델 4개 (users/payments/generations/waiting_copies)
│   │                                 #   ※ 최상위 models/ 디렉토리와 다름 — 서비스 ORM 전용
│   ├── schemas.py                    # Pydantic 요청·응답 스키마
│   ├── auth.py                       # 비밀번호 해시·세션 검증
│   ├── init_db.py                    # 테이블 생성 + 시드 데이터
│   │
│   ├── routers/                      # ★ API 라우터 (서비스 개발 담당)
│   │   ├── auth_router.py            # 회원가입·로그인·로그아웃
│   │   ├── users_router.py           # 내 정보 조회/수정
│   │   ├── generate_router.py        # 생성 요청·예상 차감 조회
│   │   ├── generations_router.py     # 이력 목록·상세·삭제
│   │   ├── payments_router.py        # 크레딧 충전
│   │   └── waiting_router.py         # 대기 문구 제공
│   │
│   ├── services/                     # ★ 비즈니스 로직 (가장 중요)
│   │   ├── usage_service.py          # 일일 무료 확인·자정 리셋
│   │   ├── credit_service.py         # 크레딧 차감·롤백·잔액 조회
│   │   └── generation_service.py     # 생성 오케스트레이션·상태 전이
│   │
│   ├── clients/                      # ★ 모델 담당 연동부 (계약 경계)
│   │   ├── chatbot_client.py         # 실제 챗봇 호출 (D7에 연결)
│   │   │                             #   → models.basic.main / models.consult.main 을 호출
│   │   └── mock_chatbot.py           # Mock 응답 (D1~D6 개발용)
│   │
│   ├── requirements.txt / pyproject.toml (uv)
│   ├── Dockerfile / .dockerignore
│   └── app.db                        # SQLite 파일 (gitignore)
│
├── frontend/                         # ★★ 서비스 개발 담당 관리
│   ├── streamlit_app.py              # 진입점 · 로그인 상태 라우팅
│   ├── api_client.py                 # 백엔드 호출 래퍼 (requests)
│   │
│   ├── pages/                        # ★ 화면 8종
│   │   ├── login.py                  # 로그인/회원가입
│   │   ├── dashboard.py              # 메인 대시보드(기능 카드 2종)
│   │   ├── basic_chatbot.py          # 기본 챗봇(게시물 생성)
│   │   ├── consultant_chatbot.py     # 컨설턴트 챗봇
│   │   ├── mypage.py                 # 마이페이지(통계·이력)
│   │   └── billing.py                # 크레딧 충전
│   │
│   ├── components/                   # ★ 공통 컴포넌트
│   │   ├── sidebar.py                # 내 가게·무료사용량·크레딧·메뉴4종
│   │   ├── credit_dialog.py          # 크레딧 동의창(예상차감·잔액)
│   │   ├── waiting_screen.py         # 대기 화면(문구 5초 랜덤)
│   │   ├── result_view.py            # 결과·승인(제안 3안)
│   │   └── error_banner.py           # 에러 배너 3종(402/429/5xx)
│   │
│   ├── requirements.txt
│   └── Dockerfile
│
├── models/                           # ★★★ 모델 코드 묶음 — backend/ 의 형제 (하위 아님)
│   │                                 #   ※ backend/ 하위에 두지 않는 이유:
│   │                                 #     ① 배포 단위 분리(모델 수정이 backend 재빌드 유발 안 함)
│   │                                 #     ② Mock 우선 전략 유지(D1~D6 backend 독립 개발)
│   │                                 #     ③ 관리자 경계 유지 ④ 추후 GPU 서버 분리 대비
│   │
│   ├── shared/                       # ★ 전민재 PM 관리 — 두 챗봇 담당자는 import만
│   │   │                             #   ※ 완전히 동일한 코드만 여기로 올린다
│   │   ├── llm.py                    # OpenAI 호출 래퍼(+429 백오프)
│   │   │                             #   ★ 두 챗봇이 100% 동일 → 통합 (중복 제거)
│   │   ├── state_common.py           # ★ CommonState — 두 챗봇 공통 GraphState (D-002)
│   │   │                             #   chatbot_type·user_id·question·store
│   │   │                             #   context·result·sources·tokens_used
│   │   │                             #   validation·source_gen_id
│   │   ├── base_nodes.py             # ★ 전민재 PM 검증 함수를 감싸는 노드 4종 공통 래퍼
│   │   │                             #   security_input · regulation · security_output · self_check
│   │   └── retry.py                  # 429 백오프·재시도 상한 공통 유틸
│   │
│   ├── basic/                        # ★★ 기본 챗봇(게시물 생성) 담당 작업 영역
│   │   ├── main.py                   # 챗봇 진입점 (서비스 개발 담당자가 호출)
│   │   ├── config.py                 # 채널 규칙·재생성 상한 등 기본 챗봇 전용 상수
│   │   │                             #   ※ 모델명·온도 등 공통값은 models/shared/ 참조
│   │   │
│   │   ├── graph/                    # ★ LangGraph 골격 (기본 챗봇 담당자가 관리)
│   │   │   ├── state.py              # BasicState — CommonState 상속 + 전용 필드
│   │   │   │                         #   platform·extra·proposals·retry_count
│   │   │   └── build_basic.py        # 노드 조립 + 조건부 엣지(재생성 루프)
│   │   │
│   │   ├── nodes/                    # ★ 기본 챗봇 담당자가 개발하는 노드들
│   │   │   ├── security_input.py     # 보안1 노드 — 전민재 PM의 check_input() 감싸기
│   │   │   ├── question_analysis.py  # 질문 분석·정보충분성
│   │   │   ├── extra_form.py         # 보조정보 폼 처리(선택사항)
│   │   │   ├── channel.py            # 채널(플랫폼) 확정
│   │   │   ├── market_for_copy.py    # 상권 카피용 요약(3층) — cache.get_market() 호출
│   │   │   ├── trend_for_copy.py     # 시즌·이슈 카피용 요약(3층) — cache.get_trend() 호출
│   │   │   ├── benchmark_node.py     # 업종 벤치마크 RAG 검색·요약(3층)
│   │   │   ├── copy_gen.py           # ★ 광고 카피 생성 (가장 중요)
│   │   │   ├── ranking.py            # 배리언트 랭킹(LLM Judge)
│   │   │   ├── regulation_node.py    # 규제검증 노드 — 전민재 PM의 check_regulation() 감싸기
│   │   │   ├── image_gen.py          # 광고 이미지 생성 노드
│   │   │   ├── image_review.py       # 이미지 자동 검수
│   │   │   ├── channel_format.py     # 채널별 리포맷
│   │   │   ├── security_output.py    # 보안2 노드 — 전민재 PM의 check_output() 감싸기
│   │   │   └── self_check_node.py    # self_check 노드 — 전민재 PM의 self_check() 감싸기
│   │   │   # ※ context_review.py 없음 — 경쟁사 리뷰는 컨설턴트 전담
│   │   │   # ※ context_trend.py 없음 — 트렌드 API 호출은 컨설턴트 전담
│   │   │   # ★ 검증 노드 4개는 D2에 모두 연결 완료
│   │   │   #   → 전민재 PM이 스텁 내용만 채우면 자동 반영
│   │   │
│   │   ├── clients/                  # ★ 외부 연동부 (교체 가능하게 분리)
│   │   │   └── image_client.py       # 1차 API → 2차 SDXL 교체 지점
│   │   │   # ※ trend_api.py 없음 — cache/trend_repo.py(컨설턴트)로 이관
│   │   │
│   │   ├── retrieval/                # 벤치마크 RAG (인덱싱·검색 = 기본 챗봇 담당 영역)
│   │   │   ├── vectorstore.py        # FAISS 인덱스 로드·검색
│   │   │   └── embedder.py           # text-embedding-3-small
│   │   │
│   │   ├── scripts/                  # ★ 기본 챗봇 담당 배치 (별도 트랙)
│   │   │   └── build_benchmark_index.py  # KB 데이터(전민재 PM 제공) → FAISS 인덱싱
│   │   │   # ※ 데이터 작성 자체는 전민재 PM/컨설턴트 영역
│   │   │
│   │   ├── eval/                     # ★ 평가 — 코드는 기본 챗봇 담당, 데이터는 전민재 PM
│   │   │   ├── eval_retrieval.py     # HitRate@5 · MRR
│   │   │   ├── eval_generation.py    # LLM Judge · Faithfulness
│   │   │   ├── eval_image.py         # CLIP Score
│   │   │   └── reports/              # 평가 결과 리포트 · 튜닝 전후 비교표
│   │   │   # ※ golden_dataset.json 은 shared_data/ 에 위치(전민재 PM 작성)
│   │   │
│   │   ├── tests/
│   │   │   └── test_pipeline.py      # 그래프 E2E 테스트
│   │   │   # ※ test_regulation.py(검증 함수 단위 테스트)는 전민재 PM 영역
│   │   │
│   │   ├── requirements.txt / pyproject.toml (uv)
│   │   └── README.md
│   │
│   └── consult/                      # ★★ 컨설턴트 챗봇 담당 작업 영역
│       ├── main.py                   # 챗봇 진입점 (서비스 개발 담당자가 호출)
│       ├── config.py                 # TTL 상수 등 컨설턴트 전용 상수
│       │                             #   ※ 모델명·온도 등 공통값은 models/shared/ 참조
│       │
│       ├── graph/                    # ★ LangGraph 골격 (컨설턴트 챗봇 담당자가 관리)
│       │   ├── state.py              # ConsultState — CommonState 상속 + 전용 필드
│       │   │                         #   strategy·reasons·suggested_chips
│       │   └── build_consultant.py   # 노드 조립 + 조건부 엣지(재생성 루프)
│       │
│       ├── nodes/                    # ★ 컨설턴트 챗봇 담당자가 개발하는 노드들
│       │   ├── security_input.py     # 보안1 노드 — 전민재 PM의 check_input() 감싸기
│       │   ├── question_analysis.py  # 질문 분석·정보충분성
│       │   ├── suggested_chips.py    # 추천 질문 칩 3종 처리
│       │   ├── market_for_consult.py # 상권·경쟁 밀도 분석 (3층, 컨설팅용)
│       │   ├── review_for_consult.py # 경쟁사 리뷰 차별점 (3층)        [COULD]
│       │   ├── trend_for_consult.py  # 시즌·수요 타이밍 (3층)
│       │   ├── strategy.py           # ★ 마케팅 전략 제안 (가장 중요)
│       │   ├── strategy_check.py     # 전략 품질 검증(근거·실행가능성)
│       │   ├── link_to_ads.py        # ★ [이 전략으로 광고 만들기] 연계
│       │   ├── security_output.py    # 보안2 노드 — 전민재 PM의 check_output() 감싸기
│       │   └── self_check_node.py    # self_check 노드 — 전민재 PM의 self_check() 감싸기
│       │   # ※ *_for_copy.py 없음 — 카피용 요약은 기본 챗봇 담당 영역
│       │
│       ├── clients/                  # ★ 외부 API 호출부 (Cache-Aside의 '미스' 경로)
│       │   ├── market_api.py         # 상권정보 OpenAPI 호출
│       │   ├── trend_api.py          # NAVER 검색어 트렌드 호출
│       │   └── review_crawler.py     # 네이버 플레이스 배치 크롤러   [COULD]
│       │   # ※ geocode_api.py 없음 — 지오코딩은 서비스 개발 담당 영역
│       │
│       ├── analysis/                 # 컨설팅 분석 유틸
│       │   ├── density.py            # 경쟁 밀도·최근접 거리 계산
│       │   └── sentiment.py          # KcELECTRA 감성분석(CPU)       [COULD]
│       │
│       ├── scripts/                  # ★ 배치 적재 (파이프라인과 분리)
│       │   ├── preload_demo_cache.py # ★ 시연용 캐시 사전 적재(강남역 등) — D9
│       │   └── load_review_cache.py  # 리뷰 사전 수집 배치          [COULD]
│       │   # ※ 상권·트렌드는 Cache-Aside라 별도 적재 배치 불필요
│       │
│       ├── eval/                     # ★ 평가
│       │   ├── eval_strategy.py      # 전략 품질 LLM Judge
│       │   ├── eval_retrieval.py     # 데이터 조회 정확도·캐시 히트율
│       │   └── reports/              # 평가 결과 · 튜닝 전후 비교표
│       │
│       ├── tests/
│       │   ├── test_market_repo.py   # Cache-Aside 동작 테스트(히트/미스)
│       │   └── test_pipeline.py      # 그래프 E2E 테스트
│       │
│       ├── requirements.txt / pyproject.toml (uv)
│       └── README.md
│
├── scripts/                          # ★ 전민재 PM 배치 스크립트 (루트)
│   ├── load_banned_keywords.py       # CSV → DB 적재
│   └── build_legal_kb.py             # ★ md → JSON → 임베딩 → FAISS 인덱싱
│
├── tests/                            # ★ 루트 테스트 — 서비스 개발 담당 + 전민재 PM
│   │                                 #   ※ 모델 테스트는 각 models/*/tests/ 에 위치
│   ├── test_auth.py                  # [서비스] 회원가입·로그인
│   ├── test_credit.py                # [서비스] ★ 과금 로직(가장 중요한 테스트)
│   ├── test_e2e.py                   # [서비스] 전체 시나리오
│   ├── test_security.py              # [PM] 보안1·2 차단 테스트
│   ├── test_regulation.py            # [PM] 규제 검증 (과잉 차단·누락 케이스)
│   └── test_self_check.py            # [PM] 답변 검증 규칙 테스트
│
├── docs/                             # ★ 팀 공용 문서 — 한 곳에 모음
│   │                                 #   ※ 흩어져 있으면 못 찾으므로 루트로 통합
│   │
│   ├── sdp_pm.md                     # [PM] 전민재 PM SDP
│   ├── sdp_service.md                # [서비스] 서비스 개발 담당 SDP
│   ├── sdp_basic.md                  # [기본] 기본 챗봇 담당 SDP
│   ├── sdp_consult.md                # [컨설턴트] 컨설턴트 챗봇 담당 SDP
│   │
│   ├── pipeline_sdp_pm.png           # [PM] 파이프라인 다이어그램
│   ├── pipeline_sdp_service.png      # [서비스] 파이프라인 다이어그램
│   ├── pipeline_sdp_basic.png        # [기본] 파이프라인 다이어그램
│   ├── pipeline_sdp_consult.png      # [컨설턴트] 파이프라인 다이어그램
│   ├── erd_sdp_service.png           # [서비스] ERD 다이어그램
│   │
│   ├── directory_structure.md        # ★ 본 통합 디렉토리 구조 (단일 소스)
│   ├── api_contract.md               # ★ 서비스 ↔ 모델 API 계약서
│   ├── validation_contract.md        # ★ [PM] 검증 함수 4종 계약서(두 담당자용)
│   ├── repo_contract.md              # ★ [컨설턴트] 조회 함수 시그니처(기본 챗봇 담당자용)
│   ├── graphstate_spec.md            # ★ [PM] GraphState 공통 규격(D1 확정)
│   ├── decisions.md                  # ★ [PM] 의사결정 로그(수치 3건 등)
│   ├── demo_scenario.md              # [PM] 발표 시연 시나리오
│   └── prompt_tuning_log.md          # ★ 프롬프트 튜닝 실험 기록(D10)
│
├── docker-compose.yml                # [서비스] 로컬 통합 실행
├── .env.example                      # [서비스] 환경변수 템플릿
├── requirements.txt / pyproject.toml (uv)   # 루트 공통 의존성
└── README.md                         # 프로젝트 최상위 안내
```

---

### 7.3 `models/shared/` 로 통합한 것과 하지 않은 것

> **판단 기준**: *"두 챗봇이 100% 같은 코드인가?"* 하나라도 다르면 분리 유지한다.

| 항목 | 두 챗봇 비교 | 판정 | 위치 |
| --- | --- | --- | --- |
| `llm.py` (OpenAI 래퍼 + 429 백오프) | **완전히 동일** | ✅ 통합 | `models/shared/llm.py` |
| 429 재시도·백오프 유틸 | **완전히 동일** | ✅ 통합 | `models/shared/retry.py` |
| GraphState 공통 필드 | 공통 + 각자 필드 | ⚠️ 공통만 통합 | `models/shared/state_common.py` |
| 검증 노드 4종 래퍼 | 전민재 PM 함수 감싸기 — 거의 동일 | ✅ 통합 | `models/shared/base_nodes.py` |
| `config.py` (모델명·온도) | 공통값은 같고 TTL·채널규칙은 각자 | ⚠️ 공통만 통합 | 공통=`shared/`, 전용=각자 |
| `main.py` | 각자 다른 그래프를 호출 | ❌ 분리 유지 | `basic/` · `consult/` |
| `graph/build_*.py` | 노드 구성이 완전히 다름 | ❌ 분리 유지 | `basic/` · `consult/` |
| `nodes/copy_gen.py` vs `strategy.py` | **하는 일이 완전히 다름** | ❌ 분리 유지 | `basic/` · `consult/` |

> **`nodes/` 를 통째로 합치지 않는 이유**: 카피 생성과 전략 제안은 목적이 다르다.
> 한 폴더에 25개 파일이 쌓이면 **오히려 못 찾는다.**

---

### 7.4 `models/` 를 `backend/` 하위에 두지 않는 이유 4가지

| # | 이유 | 설명 |
| --- | --- | --- |
| **1** | **배포 단위 분리** | `backend/`는 Dockerfile을 가진 독립 컨테이너다. 하위에 넣으면 **카피 프롬프트 한 줄 수정에도 backend 전체 재빌드·재배포**가 필요하고, FAISS·transformers 등 무거운 의존성이 backend 이미지에 포함된다 |
| **2** | **Mock 우선 전략 유지** | 서비스 SDP §3.2의 핵심 전략은 *"D1~D6 Mock으로 개발 → D7 실제 교체"* 다. backend 하위면 **D1부터 모델 코드에 의존**하게 되어 경계가 무너진다 |
| **3** | **관리자 경계 유지** | `backend/`는 서비스 개발 담당 관리 영역이다. 그 아래 다른 담당자 코드가 들어가면 **backend 리팩토링 시 남의 코드를 건드리게** 된다 |
| **4** | **추후 분리 대비** | SDXL 자체 호스팅 시 모델을 **GPU 서버로 분리**할 수 있다. backend 하위면 그때 **경로를 전부 수정**해야 한다 |

**호출 관계 (형제 구조)**

```
backend/clients/chatbot_client.py
        ↓ import
models/basic/main.py      → models/shared/llm.py 사용
models/consult/main.py    → models/shared/llm.py 사용
```

---

### 7.5 통합 시 해소한 충돌 3건

> 팀원들이 헷갈렸던 실제 원인이다. 아래대로 정리했다.

| # | 충돌 내용 | 해소 방법 |
| --- | --- | --- |
| **C-1** | `tests/` 를 서비스 담당·전민재 PM이 **각자 자기 것으로 표기** | 루트 `tests/` 에 **둘 다 배치**하고 파일명 앞에 `[서비스]`/`[PM]` 표기.<br>모델 테스트는 `models/*/tests/` 에 그대로 유지 |
| **C-2** | `docs/` 가 **루트·model_basic·model_consult 3곳**에 분산 | **루트 `docs/` 한 곳으로 통합.** 파일명이 겹치지 않아 손실 없음 |
| **C-3** | 4개 문서가 모두 **"내 담당"** 1인칭 표기 사용 | **전부 역할명으로 치환**(전민재 PM / 서비스 개발 담당 / 기본 챗봇 담당 / 컨설턴트 챗봇 담당) |

### 7.6 경로 변경 대조표

> 이미 작성한 코드가 있다면 **import 경로만** 아래대로 바꾸면 된다.

| 기존 | 변경 |
| --- | --- |
| `model_basic/` | `models/basic/` |
| `model_consult/` | `models/consult/` |
| `model_basic/llm.py` | `models/shared/llm.py` **(통합)** |
| `model_consult/llm.py` | `models/shared/llm.py` **(통합)** |
| `model_basic/graph/state.py` | `models/basic/graph/state.py` (CommonState 상속) |
| `model_consult/graph/state.py` | `models/consult/graph/state.py` (CommonState 상속) |
| `model_basic/docs/*` | `docs/*` **(루트 통합)** |
| `model_consult/docs/*` | `docs/*` **(루트 통합)** |

### 7.7 개발 시작 전 확인 사항

```
① 남의 디렉토리 파일은 import만 한다. 내부 수정이 필요하면 관리자에게 요청.
② models/shared/ 는 전민재 PM 관리 영역이다. 수정 요청은 스크럼에서 공유.
③ 루트 tests/ 에 파일 추가 시, 파일명으로 담당자가 구분되게 짓는다.
④ 문서는 전부 루트 docs/ 에 둔다. 하위에 새 docs/ 를 만들지 않는다.
⑤ requirements.txt 는 영역별로 각자 관리하되, 루트에 공통 의존성을 둔다.
⑥ 신규 디렉토리가 필요하면 스크럼에서 공유 후 추가한다.
⑦ 구조 변경은 본 문서(docs/directory_structure.md)를 먼저 고치고 코드를 옮긴다.
```