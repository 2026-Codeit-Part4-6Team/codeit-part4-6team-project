# 의사결정 로그 (decisions.md)

> **작성 규칙**: 의사결정한 날 **회의 중에** 한 줄 추가.
> **대안 칸은 비우지 않는다** — "검토했다는 증거" 기록.
> 미확정은 상태를 `보류`로 두고 Owner·Due를 적는다.

## 확정 결정

| ID | 날짜 | 결정 | 근거 | 대안 |
|----|------|------|------|------|
| D-001 | 8/11 | GraphState: 전민재 PM 공통 로직 예시 제안 → 담당자가 필드 추가 → 전민재 PM 컨펌 | 백지 시작 시 구조 충돌, 전민재 PM 단독 결정 시 필드 누락 | 담당자 초안만 / 전민재 PM 단독 |
| D-002 | 8/11 | `shared/state_common.py` 공통 파일 (관리: 전민재 PM) | 공통 필드 변경 시 한 곳만 수정 | 각자 복사 |
| D-003 | 8/11 | `context`·`validation`을 dict로 개방 | 챗봇마다 쓰는 컨텍스트·검증 개수가 다름 | 개별 필드 선언 |
| D-004 | 8/11 | `source_gen_id`를 공통 필드에 포함 | 컨설턴트가 만들고 기본 챗봇이 받음 — 양쪽 필요 | 각자 정의 |
| D-005 | 8/11 | 일일 무료 10회 (두 챗봇 공유) | 충전화면이 정책 고지 화면이라 우선 | 5회 |
| D-006 | 8/11 | 회당 차감: 컨설턴트 10 / 기본 50 | 스토리보드 두 숫자가 챗봇별 요금으로 해석 시 정합, 이미지는 비용 큼 | 일괄 10 |
| D-007 | 8/11 | 크레딧 Single Source = `users.credits` | 화면마다 계산하면 값이 어긋남 | 화면별 계산 |
| D-008 | 8/11 | 컨설턴트도 과금 | LLM+외부 API 사용, 무료 시 estimate 로직 복잡 | 무료 제공 |
| D-009 | 8/11 | 중복 과금 방지: `request_id` | Idempotency 헤더보다 초급자에게 단순 | 헤더 방식 |
| D-010 | 8/11 | 서비스명 = 매출부스터 | 스토리보드 확정값 | AdCopilot |
| D-011 | 8/11 | `blocked` 단일화 (warn/reask 미노출) | warn·reask는 모델 내부 재생성 루프에서 처리됨 | 3종 구분 |
| D-012 | 8/11 | 3안 `result_json` 저장 | 마이페이지 재사용(FR-30a)에 3안 전체 결과 필요 | 최종 선택만 저장 |
| D-013 | 8/11 | 모델 호출 동기 + 타임아웃 60초 | 이미지 p95 20초, (예) Streamlit 폴링은 구현 과함 | 202+폴링 |
| D-014 | 8/11 | HITL 발행 = `POST /generations/{id}/publish` | 상태 전이(done→published)가 명확 | 기존 API에 액션 포함 |
| D-015 | 8/11 | 비밀번호 해시 = bcrypt | SHA-256보다 안전, passlib 한 줄로 난이도 동일 | SHA-256+hmac |
| D-016 | 8/11 | 로그인 identifier = `email` | 스토리보드가 "아이디(이메일)" | username |
| D-017 | 8/11 | `banned_keywords`: JSON 먼저 → DB 나중 | 서비스 담당 DDL 대기 없이 D2 착수 가능 | 처음부터 DB |
| D-018 | 8/11 | 부분 실패 시 자리 유지 + error 필드 단일화 | 배열에서 빼면 프론트 3카드 레이아웃 깨짐 | 실패 항목 제거 |
| D-019 | 8/11 | 재생성 상한: 카피 2회 / 이미지 1회 | 이미지는 개별 호출이라 3장=API 3회, 한도 부담 | 둘 다 2회 |
| D-020 | 8/11 | 카피 1개라도 성공 시 전액 차감 | 카피가 핵심 산출물, 차등 환불은 구현 과함 | 이미지 실패 시 부분 환불 |
| D-021 | 8/11 | 크레딧 차등 유지: 기본50/컨설턴트10 | 통일 시 충전화면 문구가 거짓, 실제 비용도 다름 | 통일 50 |
| D-022 | 8/11 | 로그인 ID = username (D-016 변경) | ORM 이미 구현됨, 바꿔서 얻는 게 UI 문구뿐 | email |
| D-023 | 8/11 | 중복과금 키 = Idempotency-Key (D-009 변경) | 서비스 내부 구현 사항, 담당자 안 수용 | request_id |
| D-024 | 8/11 | result_json에서 image_b64 제외 | 3장 base64 = 행당 6MB, 이력 조회 성능 저하 | 전체 저장 |
| D-025 | 8/11 | 모델 타임아웃 60초 + 롤백(대기화면 동기 방식 구현) | 이미지 p95 20초×3장, 기본 30초면 정상건 실패 처리 | 30초 |
| D-026 | 8/11 | publish API를 SHOULD로 승격 (D8) | 승인 화면이 D8에 나오는데 API 없으면 버튼 무동작 | 후순위 유지 |
| D-027 | 8/11 | platform 3종 유지(blog 포함) | 스토리보드 버튼 3개 확정, 프롬프트 한 줄 추가로 대응 | 2종 축소 |
| D-028 | 8/11 | PR 단위 = 하나의 완결된 기능(300줄 이내) | 업무 단위는 크기 제각각, 일 단위는 미완성 코드 유입 | 업무별 / 일별 |
| D-029 | 8/11 | 디렉토리 구조 통합본 단일화 | 4개 SDP가 같은 경로를 각자 관리로 표기해 혼란 발생 | 각자 유지 |
| D-030 | 8/11 | models/{shared,basic,consult} 구조로 재편 | llm.py 등 완전 동일 코드가 두 곳에 중복 | 각자 유지 |
| D-031 | 8/11 | models/ 를 backend/ 하위에 두지 않음 | 배포 단위·Mock 전략·관리권 경계·추후 분리 4가지 | backend/models/ |
| D-032 | 8/11 | 디렉토리 구조 단일 소스 = docs/directory_structure.md | 4개 SDP가 각자 그려 혼란 발생 | SDP별 유지 |
| D-033 | 8/12 | Dependabot version updates 비활성화 (alerts는 유지) | 자동 버전 PR은 노이즈, 단 보안 취약점 알림은 받아야 함 | 전체 비활성화 |
| D-034 | 8/12 | Dependabot 취약점 13건 대응 보류 | 프로젝트 기간 중 버전 업 시 빌드 깨질 위험이 이득보다 큼 | 즉시 패치 |
| D-035 | 8/12 | models/shared/llm.py 는 컨설턴트 구현본 채택 | 이미 테스트 완료, 재작성은 낭비 | PM이 신규 작성 |
| D-036 | 8/12 | 검증 함수 4종 스텁 반환값 수정 + 계약 스모크 테스트 추가 | 명세 표기(pass/warn/block)를 코드에 복사해 TypeError 발생, import로는 안 잡힘 | 수정만 하고 테스트 없이 |
| D-037 | 8/12 | push 전 ruff --fix + pytest 로컬 실행 필수 | CI에서 import 정렬(I001)로 실패, 로컬 검증 누락이 원인 | CI만 의존 |
| D-038 | 8/13 | 골든 데이터셋 60문항 확정 (기본25/컨설턴트20/거부15) | 3개 SDP 문항 수 충돌(55/55/30) 정리 + 과잉차단 가드 5 추가 | 55문항 유지 |
| D-039 | 8/13 | 골든 데이터셋 2단계 구축 (8/14 파일럿15 → 8/19 전체60) | D8~D9 작성·검수 일정 겹침, 가이드도 "조기 구축" 권장 | D9 일괄 구축 |
| D-040 | 8/13 | 생성 영역은 정답 문장 대신 rubric 사용 | 카피·전략은 정답이 하나가 아님 | 정답 문장 기재 |
| D-041 | 8/13 | 동일업종 판정 = 상권 API 업종코드 필터(indsSclsCd/indsMclsCd), 텍스트 비교는 폴백 | "강남역 500m 카페 16곳"이 페이지 상한(최대 1000건/전체 6,691건)+텍스트 매칭 오차로 축소된 값일 가능성 큼. 근거 수치가 틀리면 전략·평가·발표가 동시에 무너짐 | 텍스트 비교 유지 / 전체 7페이지 페이징 |
| D-042 | 8/13 | 상권 조회 = 호출 2회 방식(①numOfRows=1로 전체 totalCount ②업종코드 필터+numOfRows=1000) | 6,691건 전체 페이징(7회) 대비 호출 2회로 동일업종 수 정확 확보 + 최근접 거리 계산 가능 | 전체 페이징 후 로컬 집계 |
| D-043 | 8/13 | 업종코드 매핑 단일 소스 = shared_data/industry_code_map.json (원본: 업종분류 2302 xlsx) | 텍스트 매칭 시 R10202 스터디카페 오탐·"비알코올 음료점업" 누락 발생. 각자 매핑하면 두 챗봇 결과 불일치 | 노드별 하드코딩 |
| D-044 | 8/13 | 사용자 노출 reasons는 원시 수치만, 밀도 등급은 프롬프트 내부 힌트로만 사용 | 경계값(0/1~3/4~8/9+)이 임의 근사치라 검증 불가. golden_dataset.md 판정 기준은 must_contain_number(숫자) | 등급을 사용자에게 노출 |
| D-045 | 8/13 | 등급 경계값 재조정은 D-038 교정 완료 이후 D9 [SHOULD] | 틀린 모수 위에서 경계값을 맞추면 교정 후 전부 재작업 | 즉시 재조정 / 영구 보류 |
| D-046 | 8/13 | 계약 문서 버전 변경 시 decisions.md 변경이력 1줄 + 스크럼 diff 3줄 구두 공지 의무화 | Contract v0.2→v0.3에서 D1 합의가 조용히 번복, 발견이 담당자 개인 리뷰에 의존했음 | 문서 갱신만 |
| D-047 | 8/13 | 내부 state 표현 ≠ 외부 응답 계약, 변환은 응답 직전 1곳에서만 | 계약 재변경 시 변환 함수 1개만 수정하면 됨. state를 계약 형식에 묶으면 전 노드 영향 | state를 계약 형식 그대로 사용 |
| D-048 | 8/13 | validation/ 스텁 4종 즉시 main 머지(실구현 미완이어도 pass 반환) | PM 미제공이 D3 블로커(보안1 D4 이월). sdp_pm.md §2 스텁 선제공 원칙을 PM 본인이 위반 | 실구현 완료 후 일괄 머지 |
| D-049 | 8/13 | models/shared/llm.py 이관 실행(컨설턴트 PR → PM 리뷰·머지 → 이후 PM 관리) — D-035 실행분 | 결정은 8/12에 났으나 당사자 통보 누락으로 담당자가 대기 상태였음 | 컨설턴트가 계속 보유 |
| D-050 | 8/13 | 모델명·온도·재시도 상수 단일 소스 = models/shared/config.py | 챗봇별로 모델이 갈리면 비용·품질 비교 불가, $30 한도 추적도 어려움 | 각자 config 유지 |
| D-051 | 8/13 | LLM 모델은 D5 A/B(3문항) 후 확정 — 현재 gpt-4o-mini 유지 | 코드잇 가이드 권장은 GPT-5.4 Nano/Mini 계열이나, D4(M3) 진행 중 변수 추가 시 원인 분석 불가 | 즉시 교체 / 현행 확정 |
| D-052 | 8/13 | call_llm에 요청 데드라인(50초) 적용 — 잔여 시간 < 다음 백오프면 재시도 포기·폴백 | 백오프 14초+4회 호출이 D-025 60초 타임아웃과 충돌. LLM 사용 노드가 4곳이라 429 2회면 초과 | 재시도 3→2회 축소 |
| D-053 | 8/13 | market_cache 중복 방지 = upsert 선적용, UNIQUE 인덱스는 D7에 서비스 담당이 추가 | 서비스 담당 DDL 대기 없이 방어 가능(D-017과 동일 패턴) | DDL 완료까지 대기 |
| D-054 | 8/13 | 컨설턴트 골든 데이터셋 20문항(C-)을 D4~D6 노드 완성 시 유형별 적립 | golden_dataset.md v1.0이 SDP의 30문항을 20으로 정정. D9 일괄 작성은 지연 시 통째로 누락 | 30문항 유지 / D9 일괄 작성 |
| D-055 | 8/13 | 캐시 적중률을 발표용 정량 지표로 승격(로그 집계 스크립트 추가) | 히트/미스 로깅이 이미 완료돼 추가 비용 최소, SDP §8.2 ★ 지표. "API 호출 N회 절감" 발표 근거 확보 | 로그만 유지 |
| D-056 | 8/13 | 캐시 TTL 확정 = 상권 7일 · 트렌드 7일 · 리뷰 30일 (P-006 종료) | D1+D2에서 cache/ttl.py로 구현·검증 완료, 원본 API가 stdrYm 단위 갱신이라 7일 근거 성립 | 전 데이터 통일 TTL |
| D-057 | 8/13 | 크레딧 단가 = 기본 50 / 컨설턴트 10 재확인 (Contract v0.3·config·테스트를 수정) | 기본 챗봇은 카피3+이미지3으로 실제 최대 비용, D-006·D-021이 이미 확정한 값. 계약 문서가 반대로 기재돼 코드·테스트까지 전파됨 | 계약값(기본10/컨설턴트50) 채택 |
| D-058 | 8/13 | 정책·수치의 상위 소스 = decisions.md, 필드 형태의 상위 소스 = Contract 문서. 충돌 시 계약을 고친다 | D-054가 "담당자는 계약을 성실히 구현했는데 계약이 틀린" 사례. 소스 우선순위가 없으면 재발 | 계약 문서 우선 |
| D-059 | 8/13 | 모델→서비스 인바운드 스키마는 extra="ignore", 프론트→서비스는 extra="forbid" 유지 | 모델이 필드 1개만 추가해도 전체 생성 실패. 반대로 프론트 미정의 필드는 S-05가 422를 요구 | 전부 forbid / 전부 ignore |
| D-060 | 8/13 | ModelResult 파싱은 chatbot_type으로 명시 분기, 스마트 Union 미사용 | Basic·Consultant가 status="ok"를 공유해 판별자가 없음. 실패 시 4브랜치 에러로 원인 추적 불가 | Union 스마트 매칭 유지 |
| D-061 | 8/13 | 캐시 테이블은 관리자(컨설턴트)가 자기 Base로 생성, 서비스 init_db는 4종 유지 | DATABASE_URL 통합 후 market_cache 생성 주체 부재 → 캐시가 에러 없이 항상 미스(R5·R12 대비책 무력화) | 서비스 init_db에 포함 / D7까지 방치 |
| D-062 | 8/13 | SQLite 공유 파일에 WAL + timeout 30초 적용 | 서비스(generations)와 컨설턴트(market_cache)가 같은 파일에 동시 쓰기 → database is locked 위험 | 기본 설정 유지 |
| D-063 | 8/13 | DB 시각은 naive UTC 저장, 읽는 즉시 UTC 부여 (models/shared 헬퍼 1개) | SQLite가 tz를 저장하지 않아 aware/naive 비교 TypeError 발생. UsageService(S-06)와 cache/ttl.py 양쪽에 영향 | 각자 처리 |
| D-064 | 8/13 | 테스트는 개발 DB(./data/app.db) 사용 금지 — conftest에서 DATABASE_URL을 메모리로 고정 + get_db를 dependency_overrides로 tmp DB 세션 주입 + 회귀 테스트 1개 | conftest가 전역 engine을 써서 ①재실행 시 users.username UNIQUE 충돌로 간헐 실패 ②DATABASE_URL 통합 후 같은 파일의 시연용 market_cache가 rm 한 번에 소실(R12 대비책 무력화) ③공유 VM에서 타인 화면에 테스트 데이터 노출 | 현행 유지 / 테스트마다 수동 정리 |
| D-065 | 8/13 | StoreContext 구성은 크레딧 차감 이전에 수행, 실패 시 422 | users.lat/lng·business_name이 nullable이라 좌표 없는 사용자에서 500 발생 가능 | 모델 호출 직전 구성 |
| D-066 | 8/13 | Preview /generate → /preview/generate 이동 + include_in_schema=False, D4에 삭제 | 계약 엔드포인트와 경로가 같아 프론트·시연에서 오인 가능, 인증도 없음 | 현행 경로 유지 |
| D-067 | 8/13 | 임시안 enum(payments.package·status)은 DB CHECK 대신 앱 계층 검증. 스키마 변경 시 개발 DB 재생성 | Alembic 미도입 + SQLite라 CHECK 변경이 테이블 재생성 수준. 임시안을 DB에 굳히면 변경 비용이 큼 | Alembic 도입 / CHECK 유지 |
| D-068 | 8/13 | 설계 골격 PR은 D-028(300줄) 예외, 단 PR 본문에 사유 명시 | 구조·ORM·DTO·Mock은 쪼개면 오히려 중간 상태가 깨짐. 예외를 인정하되 무제한 확대는 방지 | 300줄 엄격 적용 |
| D-069 | 8/13 | ERD 이미지를 코드 기준으로 갱신 | source_gen_id 실제 self-FK, payments.status 기본 pending, idempotency_key·request_hash·result_json·selected_proposal_index 누락 — 발표 자료에 그대로 들어감 | 이미지 유지 |
| D-070 | 8/13 | .env.example의 상권 API 키 주석(디코딩 키 사용) 복원 | 공공데이터포털 인코딩/디코딩 키 혼동은 실호출로만 발견되는 삽질 포인트, 컨설턴트가 확인한 지식 | 축약본 유지 |
| D-071 | 8/13 | regulation은 차단 카피를 배열에서 삭제하지 않고 error 슬롯으로 치환 | passed+failed 방식은 proposals가 2개가 되어 서비스 min_length=3에서 ValidationError(502). D-018 재확인 | 삭제 유지 / 프론트에서 3칸 패딩 |
| D-072 | 8/13 | ranking LLM은 텍스트 대신 index+score 반환, 재정렬은 코드가 수행 | LLM이 개수를 줄이거나 카피를 몰래 고쳐 써도 계약이 안 깨짐. 개수 보존·원문 보존·실패항목 보존이 동시에 해결 | LLM 출력 그대로 신뢰 |
| D-073 | 8/13 | 모델 error 응답 reason 매핑 확정 (copy_generation_failed→provider_error, 429→rate_limit, 타임아웃→timeout, 그 외 unknown) | assemble_response에 reason 자체가 없고 내부 코드가 계약 enum 밖이라 ErrorResult 검증 실패 | 내부 reason 그대로 노출 |
| D-074 | 8/13 | extra 필드명은 계약 5종 고정(purpose·price_range·target_age·strength·clarification), 모델 테스트도 계약명 사용 | 모델 측이 target_customer·selling_point를 쓰고 있으나 서비스가 extra="forbid"라 422 | 모델 측 이름 허용 |
| D-075 | 8/13 | 이미지 CLIP 검수는 MVP에서 비차단(점수 기록만), 게이트 승격은 D9 분포 확인 후 | clip-vit-base-patch32는 영어 전용인데 한국어 카피로 채점 → 임계값 0.25 통과 곤란 → 상시 재생성. FR-13b도 CLIP을 개발용 평가 지표로 규정 | 차단 게이트 유지 / CLIP 제거 |
| D-076 | 8/13 | 이미지 없음(미생성)은 reject가 아니라 pass, 이미지 재생성 상한 1회, retry 카운터를 copy/image로 분리 | generate_image()가 None 반환 → 요청당 이미지 6장 구조. 공유 카운터 탓에 copy 재시도가 규제 재생성 예산을 잠식 | 공유 카운터 유지 |
| D-077 | 8/13 | models/basic/llm.py 삭제 → models/shared/llm.py 사용 (D-035·D-046·D-047 실행) | 동일 코드 3중화, 챗봇별 모델이 갈리면 $30 예산 추적·품질 비교 불가 | 각자 보유 |
| D-078 | 8/13 | 임베딩 등 모든 OpenAI 호출은 shared 래퍼 경유(429 백오프 일원화) | embedder.py가 OpenAI() 직접 호출 — 벤치마크 인덱싱은 연속 임베딩이라 429 최다 발생 지점(add 17·18) | 노드별 개별 처리 |
| D-079 | 8/13 | trend 조회 키워드는 question_analysis가 추출한 keyword 사용, 질문 원문 금지 | 원문은 매번 달라 캐시 적중률 0 → NAVER 월 5만건 한도 직접 소모, 컨설턴트 Cache-Aside(R5) 무력화. 기존 LLM 호출에 필드 1개 추가라 추가 비용 0 | 질문 원문 유지 |
| D-080 | 8/13 | torch·transformers·faiss는 basic 전용 그룹 + 지연 import, CLIP 미가용 시 점수 없이 통과 | 모듈 최상단 import라 build_basic_graph()만 불러도 torch 로드. CI 설치 시간·D7 백엔드 이미지 비대화·오프라인 가중치 다운로드 실패 | 현행 유지 |
| D-081 | 8/13 | LLM provider 이원화: 운영·시연·평가 산출 = 코드잇 OpenAI, 로컬 대량 실험 = 대체 provider 허용(사용 시 기록 필수) | Groq(Llama-3.3) 사용 사실이 보고서에만 있고 결정 기록 없음. 발표 시 "무슨 모델로 낸 수치냐"에 답할 수 있어야 함 | OpenAI 전용 / 자유 사용 |
| D-082 | 8/13 | 모델·provider 교체 시 PR "실험 결과" 섹션 + docs/prompt_tuning_log.md 전후 비교표 작성 필수 | 평가항목 "모델 선택 이유"·"성능 개선 시도"에 직결. 이번 Groq→OpenAI 교체가 미기록 | 구두 공유로 갈음 |
| D-083 | 8/13 | platform = instagram·banner 2종 확정, blog 제외 (D-027 변경) | Contract v0.3 및 서비스 Literal이 2종, 코드도 2종. D-027만 낡은 상태로 남아 충돌 | blog 복원 |
| D-084 | 8/13 | title은 question_analysis 반환값 사용(30자 자르기 폐기) | 마이페이지 생성 이력(FR-30)에 잘린 제목이 그대로 노출. 기존 LLM 호출에 필드 추가라 비용 0 | 요약 전용 LLM 호출 추가 |
| D-085 | 8/13 | models/shared/llm.py 를 골든 데이터셋 문항 작성보다 우선 착수 | 두 담당자가 각자 우회 파일로 진행 중(중복 2벌), 호출 지점이 매일 증가해 이관 비용이 복리. 골든 데이터셋은 기준 문서 완료 + PM 몫(R- 15문항) 마감이 D9 | 골든 데이터셋 우선 |
| D-086 | 8/13 | shared/llm.py = 컨설턴트 뼈대 + 기본의 (text, tokens)·json_mode 합집합 (D-035 수정) | 컨설턴트 버전은 -> str 이라 tokens_used를 못 채움. Contract v0.3에서 tokens_used는 Basic·Consultant 양쪽 필수 필드 | 컨설턴트본 그대로 / 기본본 그대로 |
| D-087 | 8/13 | call_llm 반환은 tuple[str, int] 단일 시그니처, json_mode 기본값 False | 기본값 False면 컨설턴트 기존 호출 동작이 불변이라 D4 작업 중단 없이 이관 가능 | str 반환 + 별도 함수 추가 |
| D-088 | 8/13 | OpenAI 클라이언트는 모듈 싱글턴(_get_client) + 테스트용 reset_client | 호출마다 생성 시 httpx 커넥션 풀이 매번 새로 생성 — 골든 데이터셋 100문항 평가 루프에서 소켓 누수 | 호출마다 생성 |
| D-089 | 8/13 | LLM_TIMEOUT_SECONDS(20) 단일 호출 상한 + LLM_DEADLINE_SECONDS(50) 요청 예산 (D-052 구현) | 백오프 14초 + 4회 호출이 서비스 60초 타임아웃을 잠식. 남은 예산 < 다음 대기시간이면 재시도 포기 | 재시도 횟수 축소 |
| D-090 | 8/13 | 백오프 인덱스는 min(attempt, len-1), 루프 종료 시 RuntimeError 명시 | 원본은 MAX_RETRIES를 늘리면 IndexError, 루프 이탈 시 암묵적 None 반환 | 원본 유지 |
| D-091 | 8/13 | OPENAI_BASE_URL 을 env로 노출 (provider 교체 지점 일원화) | D-081(로컬 실험용 대체 provider 허용)을 코드로 실행. OpenAI 호환 엔드포인트면 env 한 줄로 교체 | 코드 수정으로 교체 |
| D-092 | 8/13 | get_total_tokens() 누적 카운터 제공 | PM의 $30 예산 관리(sdp_pm §5.4)와 !usage 교차 확인, 발표용 "평균 토큰/요청" 수치 확보 | 노드별 개별 집계 |
| D-093 | 8/13 | models/consult/config.py 는 shared/config 재노출로 무중단 이관, D7에 재노출 삭제 | 컨설턴트가 D4 전략 노드 작업 중이라 import 경로를 깨면 당일 작업이 멈춤 | 즉시 전면 교체 |
| D-094 | 8/13 | 파일 관리권 준수 — PM은 models/shared/ 만 PR, 호출부 import 변경은 각 담당자 PR | sdp_consult §5.3 파일 관리권. PM이 남의 노드까지 고치면 머지 충돌 | PM이 일괄 수정 |
| D-095 | 8/13 | models/shared/config.py 는 신설이 아니라 문서 누락 보완으로 처리 | directory_structure §7.3이 "config.py 공통값=shared/"로 이미 판정했고 basic·consult 트리 주석도 "공통값은 models/shared/ 참조"라 표기 — §7.2 그림에만 빠져 있었음 | 신규 결정으로 취급 / 각자 config 유지 |
| D-096 | 8/13 | models/shared/retry.py 는 만들지 않고 llm.py에 흡수, 문서에서 제거 | 컨설턴트 구현본 채택(D-035)이 백오프를 llm.py 인라인으로 구현했고 사용처가 llm.py 하나뿐. 분리 시 통과한 테스트 5개 재작성 + 파일 3개 얽힘. config.py 추가와 상쇄되어 shared/ 파일 수 순증 0 | retry.py 별도 생성 |
| D-097 | 8/13 | directory_structure.md 트리에 상태 마커 표기([완료]/[날짜]/[미정]) | 문서에 그려졌으나 실재하지 않는 파일 3종(llm·retry·base_nodes) 때문에 두 담당자가 각각 우회 파일을 만듦 — 계획과 현실이 구분되지 않는 게 원인 | 현행 유지 |
| D-098 | 8/13 | 설정값 단일 관리 원칙: LLM 설정=models/shared/config.py, 챗봇 전용=각자 config.py, 서비스 정책값=backend/config.py, 비밀값=.env. 타 영역 값 복사 금지 | D-057(크레딧 단가 반전)가 같은 값이 두 곳에 존재해 생긴 사고. 모델 쪽은 서비스 타임아웃을 복사하지 않고 더 짧은 자체 데드라인(50초)만 둔다 | 필요 시 복사 허용 |
| D-099 | 8/13 | models/shared/base_nodes.py 통합은 D7로 이월, 문서에 [D7] 표기 | 두 담당자가 이미 검증 노드 래퍼를 각자 구현 중이라 지금 통합하면 양쪽 작업 파일을 동시에 건드려 충돌. 계약이 안정된 D7이 적기 | 즉시 통합 / 문서에서 삭제 |
| D-100 | 8/13 | shared 테스트는 이관(5종)+추가(3종) 8개를 한 파일에 완결 구성, 헬퍼 포함 | 추가분만 붙여 넣어 _rate_limit_error 헬퍼 누락 → CI NameError. 테스트 모듈은 독립이라 타 파일 헬퍼를 공유하지 않음 | 헬퍼를 conftest로 분리 |
| D-101 | 8/13 | models/consult/llm.py·test_llm.py 삭제는 컨설턴트 노드 import 전환 확인 후(D5) | 컨설턴트 D4 전략 노드가 아직 해당 모듈을 사용 중 — 선삭제 시 당일 작업 중단 | 이번 PR에서 즉시 삭제 |
| D-102 | 8/13 | 로컬 검증 명령을 CI와 동일 문자열로 고정(uv run --locked --all-groups pytest) | 파일 단위 실행은 모듈 간 문제를 못 잡음. 전체 134개가 2.26초라 비용 사유 없음. D-037 재발(PM 본인) | 파일 단위 실행 허용 |
| D-103 | 8/13 | 인바운드 정책은 InboundModel 베이스 클래스로 표현(StrictModel 상속 후 override 금지) | 선언 줄이 StrictModel인데 실제는 non-strict라 리뷰어 오해 소지, model_config 4중 중복. 방향(모델→서비스)을 타입 이름에 인코딩 | 현행 override 유지 |
| D-104 | 8/13 | 무시한 미정의 필드를 INFO 로그로 남긴다 | extra=ignore로 기본값 있는 선택 필드(sources·suggested_chips)가 오타 시 조용히 빈 배열이 됨 — 추천 칩·근거가 에러 없이 사라짐 | 무음 무시 |
| D-105 | 8/13 | D-060(chatbot_type 명시 분기) 우선순위 상향, D-104 로깅과 동일 PR로 묶음 | 완화로 Basic/Consultant 구분 근거가 '필수 필드 부재' 하나만 남음. union 파싱 중에는 실패 브랜치에서도 무시 로그가 찍혀 노이즈 | 각각 별도 진행 |
| D-106 | 8/13 | 계약 구분 테스트는 실패 사유(missing 필드)까지 assert | dict 키 중복 시 파이썬이 조용히 뒤엣값 채택 → 테스트가 엉뚱한 이유로 통과. 완화 후 구분 근거가 하나뿐이라 사유 고정이 필수 | ValidationError 발생만 확인 |
| D-107 | 8/14 | 리뷰 항목·PR 제목은 순번 대신 결정 ID(D-###)로 지칭 | PR마다 번호가 리셋돼 같은 항목이 2번/3번으로 갈려 담당자 확인 왕복 발생. git log --grep="D-060"로 결정↔커밋 추적 가능 | PR별 순번 유지 |
| D-108 | 8/14 | ModelResult 분기는 status 봉투(_ModelResultEnvelope) 선검증 후 chatbot_type 분기 (D-060 구현안 상향) | PM 예시안의 raw.get("status")는 status 누락 시 성공 브랜치로 떨어져 엉뚱한 필드 에러 발생. Literal 선검증이 "알 수 없는 status"를 명확한 실패로 만듦 | PM 예시안 그대로 |
| D-109 | 8/14 | 어댑터는 dict와 Pydantic 객체를 모두 수용(model_dump(by_alias=True)) | Mock은 Pydantic 객체, 실제 모델은 dict 반환 — D7 교체 시 호출부 수정 불필요. alias(copy_text→copy) 보존 필수 | dict만 수용 |
| D-110 | 8/14 | D-104(무시 키 로깅) 단독 PR 진행 허용 — D-060 완료로 선행 제약 해소 | union 파싱 중 실패 브랜치 로그 노이즈가 근본 이유였고 #89로 union 제거됨 | 묶음 PR 유지 |
| D-111 | 8/14 | 모델 응답 검증 실패 시 payload를 로그에 기록, 단 image_b64 제외·길이 제한 | ValidationError만으로는 D7에 모델이 실제로 보낸 내용을 알 수 없음. base64 3장(약 6MB)이 로그에 들어가면 D-024와 같은 문제가 로그에서 재현 | 예외만 전파 |
| D-112 | 8/14 | test_consultant_result.py 중복 키 정리는 D5로 이월 | #89의 어댑터 테스트가 동일 검증을 더 강하게 수행해 커버리지는 확보됨 — 거짓 초록불 제거는 정리 작업 | 즉시 수정 |
| D-113 | 8/14 | 로깅 표준: 파이썬 logging 모듈, logger=getLogger(__name__), %s 지연 포맷, 정상 흐름=INFO / 복구 가능한 실패=WARNING | 컨설턴트 cache/market_repo.py 관례(히트=info, DB실패=warning)를 서비스로 확장. 프로젝트 가이드 "서비스 완성도" 평가항목에 로깅·모니터링 포함 | print / 담당자별 자유 |
| D-114 | 8/14 | 로그 마스킹 유틸(backend/logging_utils.py) — image_b64·키·비밀번호는 값 대신 표시, 문자열 300자·payload 2000자 상한 | base64 3장 약 6MB(D-024). GitHub Actions 로그는 저장소 접근자 전원에게 노출 | 원본 그대로 기록 |
| D-115 | 8/14 | 로그도 테스트로 잠근다(caplog로 레벨·마스킹 검증) | "남긴다"가 아니라 "안전하게 남긴다"가 요건. 컨설턴트가 이미 로그 테스트 3종 선례 보유 | 육안 확인 |
| D-116 | 8/14 | LOG_LEVEL 환경변수 + create_app()에서 basicConfig(force=True) | uvicorn이 자기 로거만 설정해 앱 로그가 출력되지 않음. 시연 시 WARNING으로 상향 가능 | 하드코딩 |
| D-117 | 8/14 | 외부 API 클라이언트는 실제 키 실호출 1회 결과를 PR에 첨부해야 승인 | mock은 우리가 가정한 응답이라 엔드포인트·헤더·필드명 오류를 못 잡음. 지오코딩 실패 시 users.lat/lng 부재 → StoreContext 필수 위반 → 컨설턴트 상권 파이프라인 전체 불능 | mock 검증만으로 승인 |
| D-118 | 8/14 | 실호출 테스트는 @pytest.mark.live + addopts="-m 'not live'"로 CI 제외, 로컬 수동 실행 | CI에 키를 넣을 수 없고 testpaths에 tests가 포함돼 기본 수집됨. GitHub Actions 로그 노출 위험도 회피 | CI에 키 등록 / 테스트 미작성 |
| D-119 | 8/14 | 로그인 실패 시 계정 부재에도 더미 해시로 verify_password 수행 | 응답 본문은 동일하나 bcrypt 미수행으로 1ms vs 250ms 차이 발생 — S-07(계정 존재 여부 비노출)이 절반만 충족. 검증은 호출 여부로(시간 assert는 CI 불안정) | 현행 유지 |
| D-120 | 8/14 | 무료 사용량 리셋 판정을 resolve_daily_free()로 분리, 조회·차감이 공유 | D3 UsageService가 동일 규칙을 복사하면 화면 표시와 실제 차감이 어긋남(D-098 단일 관리 원칙의 로직 적용) | D3에서 별도 구현 |
| D-121 | 8/14 | "await 앞에서 트랜잭션 종료" 를 팀 규칙으로 승격, D4 /generate에 적용 | 모델 호출 최대 60초(D-025) 동안 SQLite 잠금 보유 시 동시 요청이 database is locked. D2 register가 이미 올바른 선례 | 단일 트랜잭션 유지 |
| D-122 | 8/14 | geocoding fallback 사용 시 응답·사용자 레코드에 표시를 남기고 화면 안내 | demo 환경에서 전 사용자가 강남역 좌표가 되는데 로그 경고만으론 시연 중 인지 불가 → 상권 분석이 무관한 결과를 냄 | 로그 경고만 유지 |
| D-123 | 8/14 | 주소는 개인정보로 취급 — 로그 마스킹 대상(REDACT_KEYS)에 추가 | GeocodingNotFound(address)가 트레이스백에 원문을 남김. D-114 로그 마스킹 정책의 확장 | 현행 유지 |
| D-124 | 8/14 | /generate 순서 확정: StoreContext → generation INSERT(idempotency) → reserve → commit → await 모델 → 새 트랜잭션 정산 | Reservation은 초과 사용만 막고 중복 과금은 못 막음. UNIQUE(user_id, idempotency_key)가 차감보다 먼저 터져야 재차감이 없음(D-023·S-04). commit이 await보다 앞이어야 SQLite 잠금 60초 보유를 피함(D-121) | reserve 먼저 / 단일 트랜잭션 유지 |
| D-125 | 8/14 | 같은 Idempotency-Key 재요청은 request_hash 일치 시 기존 generation 반환, 불일치 시 409 | S-04 계약. 더블클릭·네트워크 재시도에서 재차감 방지 | 항상 새 generation |
| D-126 | 8/14 | 좌표 없는 사용자(StoreContext 구성 실패)는 차감 이전에 422 | 차감 후 실패하면 롤백 경로를 타야 하고 사용자에겐 원인 불명 오류가 됨 | 모델 호출 직전 구성 |
| D-127 | 8/14 | 서비스 오류 detail 형식 통일: {"code","message"} 필수, 부가 필드는 추가만 | 402만 {"required","current"} 형태라 D5 프론트가 예외 분기 필요. 크레딧 부족은 "충전하러 가기" 분기가 필요해 code가 있어야 함 | 402 현행 유지 |
| D-128 | 8/14 | estimate의 크레딧 부족은 200이 아닌 402 | GenerateEstimateResponse.credits_after가 ge=0이라 음수 잔액을 표현 불가 — 200으로 바꾸려면 계약 변경 필요 | 200 + 음수 허용 |
| D-129 | 8/14 | GenerateRequest에 max_accepted_credits 추가 (계약 변경, Contract §4.3 갱신) | estimate 시점과 차감 시점 사이 상태 변화로 동의 금액을 초과 차감하는 것을 방지. 스토리보드 동의창 문구의 정합성 확보 | 필드 미도입 |
| D-130 | 8/14 | D5 프론트는 estimate의 estimated_credits를 그대로 max_accepted_credits로 전송 | 가드가 프론트 협조에 의존 — 임의값 전송 시 무력화. 미공지 시 그냥 안 쓰이는 필드가 됨 | 프론트 자유값 |
| D-131 | 8/14 | D-062(WAL + timeout=30) 즉시 적용 | 동시 쓰기 코드·테스트가 실제로 생김. D4에 market_cache 쓰기가 같은 파일에 겹치면 경합 발생 | D7까지 보류 |
| D-132 | 8/14 | CAS 차감 직후 db.refresh(user) 필수 | synchronize_session=False라 ORM 식별맵이 갱신되지 않아 라우터의 user.credits가 낡은 값 | 현행 유지 |
| D-133 | 8/14 | 코드 리뷰는 GitHub Files changed 탭에서, PR 본문에는 요약만 | 3개 PR 연속으로 diff 붙여넣기 흔적과 실제 파일을 구분하는 왕복 발생. 라인 코멘트로 추적성도 확보 | PR 본문 코드 첨부 유지 |
| D-134 | 8/14 | 테스트는 create_app() 사용, 전역 app 사용 금지 / 파일명에 버전 접미사 금지 | test_billing_v2.py가 전역 app을 override — 정리 실패 시 타 테스트로 누출. "v2"는 나중에 v1이 무엇이었는지 알 수 없게 함 | 현행 유지 |
| D-135 | 8/14 | PR 템플릿에 검증 명령(uv run --locked --all-groups pytest / ruff)을 미리 채워 넣고 체크박스로 확인 | 동일 오타(pytes)가 3개 PR 연속 발생 — 개인 부주의가 아니라 원본 복사 문제. 템플릿에 고정하면 타이핑 자체가 사라지고 D-037 로컬 검증도 함께 강제됨 | 리뷰에서 매번 지적 |
| D-136 | 8/14 | 코드·테스트 파일명에 버전 접미사(_v2, _new, _old, _final) 금지 — 이름은 "무엇을 하는가"로 | 버전 추적은 Git의 역할이고 파일명 버전과 이중화됨. test_billing_v2.py는 v1이 존재한 적 없어 추적 불가능한 질문만 남김. v3가 생기면 v2 삭제 여부가 또 미결 | 파일명 버전 허용 |
| D-137 | 8/14 | 문서는 버전 표기 유지(요구사항 v10, Contract v0.3) — 코드와 기준을 다르게 적용 | 문서는 담당자별로 서로 다른 버전을 동시에 참조하며 번복 이력 자체가 협업 정보(v0.2→v0.3 컨설턴트 응답 구조). 코드는 항상 최신 하나만 실행 | 문서도 버전 제거 |
| D-138 | 8/14 | tests/api/test_billing_v2.py → test_generate_estimate.py 로 rename (후속 정리 PR) | 내용이 /generate/estimate 전용이라 "billing"은 범위 과대. 같은 폴더 관례(test_auth_registration·test_auth_session·test_health_readiness)와 통일 | 현행 유지 |
| D-139 | 8/14 | strategy 노드: 형식 오류(summary·actions)는 즉시 실패, 품질 부족(reasons)은 재생성 2회 | 형식 오류는 재시도해도 반복되고 계약(v0.3 §6.4) 위반이라 서비스가 거부. reasons는 JSON 구조가 유효한 내용 부족이라 재생성 가치 있음 | 전부 재시도 / 전부 즉시 실패 |
| D-140 | 8/14 | 재생성 시 RETRY_REASONS_HINT 부가 + "수치 날조 금지" 방어 문구 포함 | 동일 프롬프트 반복은 동일 출력 확률이 높음. 재생성 압박 시 LLM이 없는 상권 수치를 만들어내는 것이 전형적 실패 모드 | 동일 프롬프트 반복 |
| D-141 | 8/14 | json_mode는 엄격 노드(strategy)에만, 폴백 노드(question_analysis)에는 미적용 | 폴백 경로 테스트 11개가 실전에서 실행되지 않아 검증 의미 상실. json_mode는 형식만 보장하고 필드 타입은 보장하지 않아 폴백은 어차피 필요 | 전 노드 적용(폴백 테스트 정리 조건) |
| D-142 | 8/14 | 검증 함수 4종 실구현을 P-002(8/19) 그대로 유지 → 필요 시 8/18로 상향 | 컨설턴트 보안 노드가 판정만 저장하고 차단하지 않는 상태. golden_dataset 거부 문항 15개(R-)가 라우팅을 전제 — 미구현 시 발표 안전성 섹션 공백 | 8/19 유지 |
| D-143 | 8/14 | status·issues를 CommonState로 승격(현재 BasicState에만 존재) | 두 챗봇이 차단 결과를 다르게 표현하면 서비스가 두 벌의 처리 코드를 가짐. D-002(공통 필드 단일 관리) 취지 | ConsultState에 개별 추가 |
| D-144 | 8/14 | 그래프 진입 시 state["deadline"] 설정, 모든 call_llm에 전달 | D-049 deadline은 개별 호출만 보호. strategy 최대 3회 + 429 백오프 14초 + D6/D9 노드 추가 시 60초 초과 가능 | 개별 호출 보호만 유지 |
| D-145 | 8/14 | security_output 검증 대상 = summary + actions[].content + reasons[] | 셋 다 사용자에게 노출되는데 summary만 검증 중 — actions에 민감정보가 있으면 통과 | summary만 |
| D-146 | 8/14 | retry_count는 누적(state.get + 1), 덮어쓰기 금지 | D9 strategy_check도 재생성 루프 예정이라 노드 간 카운터가 서로를 지움 | 노드별 덮어쓰기 |
| D-147 | 8/14 | strategy few-shot 예시의 reasons를 원시 수치 중심으로 수정 | D-044(등급은 프롬프트 내부 힌트, 사용자 노출은 원시 수치)과 예시가 정반대 — LLM이 예시를 그대로 따라 등급을 근거로 출력 | 현행 예시 유지 |
| D-148 | 8/14 | 검증 노드는 부분 업데이트 dict만 반환, state 제자리 수정·전체 반환 금지 | 전체 반환 시 리듀서가 붙은 필드(context·validation)에 중복 병합, 병렬 노드에서 상호 덮어쓰기. 두 챗봇 실제 구현이 이미 부분 반환 | 계약서 v1.0 예시 유지 |
| D-149 | 8/14 | 차단 결과 표현은 state["blocked"] → issues 리스트 append로 통일 | 여러 노드가 각자 append 가능하고 assemble_response가 issues[-1]을 사용. 두 챗봇 구현이 모두 issues 사용 중 | blocked dict 유지 |
| D-150 | 8/14 | validation은 반드시 기존 값과 병합해 반환({**state.get("validation",{}), ...}) | 컨설턴트가 통째 교체 방식이라 CommonState에 병합 리듀서가 없으면 앞 노드 판정이 소실. 명시 병합은 리듀서 유무와 무관하게 안전 | 리듀서에 의존 |
| D-151 | 8/14 | 라우팅 신호로 새 키(_goto) 생성 금지 — status·validation·*_retry_count로 판단 | 상태 스키마에 없는 키는 LangGraph가 거부하거나 버려 라우팅이 조용히 깨짐 | _goto 방식 |
| D-152 | 8/14 | add_conditional_edges에 path_map 필수, END는 langgraph.graph의 센티널 사용 | "END" 문자열 반환은 동작하지 않음. 계약서 v1.0 §8.3 예시가 런타임 오류 | 문자열 반환 |
| D-153 | 8/14 | check_output 반환에 masked_text 추가 (V-02 확정) | §6.3이 마스킹을 요구하는데 반환값에 마스킹 텍스트가 없어 구현 불가능. 두 챗봇이 각자 정규식을 만들면 가리는 범위가 달라짐(§13-③ 동일 논리) | 노드가 직접 마스킹 / warn도 그냥 통과 |
| D-154 | 8/14 | check_output은 텍스트 조각별로 호출(기본=카피 3안, 컨설턴트=summary+actions+reasons) | 키워드 매칭(LLM 모델 API 호출 횟수 0회)이라 다회 호출 비용 없음. 합쳤다 나누는 처리가 불필요해지고 D-145(검증 범위)도 함께 해결 | 전체 텍스트 1회 호출 |
| D-155 | 8/14 | 법률 규제검증은 카피 3안 전부 판정, block 슬롯은 삭제 대신 error 슬롯 치환 | v1.0 예시가 proposals[0]만 검증 — 2·3안이 무검증 통과. 삭제 시 3안 고정 계약 위반(D-018·D-071) | 첫 안만 검증 |
| D-156 | 8/14 | 재시도 카운터 분리: copy_retry_count / self_check_retry_count | 공유 시 규제 재생성이 카운터를 소진해 self_check 재생성 기회 소멸(D-146 연장) | 단일 retry_count |
| D-157 | 8/14 | self_check reject 재시도 실패 시 issues.reason = "unknown" (ErrorResult enum 준수) | self_check_failed 등 enum 밖 값 사용 시 서비스 ErrorResult 검증 실패 → 502 (D-073 재발) | 내부 reason 그대로 |
| D-158 | 8/14 | 컨설턴트 regulation_node 미구현 확정 + 근거를 계약서 §8.6에 명시 | check_regulation 대상이 "생성된 카피"이고 컨설턴트 산출물은 전략 조언. 광고화 경로는 link_to_ads → 기본 챗봇 파이프라인뿐이라 이미 커버. 근거 미기재로 동일 질문 반복 발생 | 컨설턴트에도 추가 |
| D-159 | 8/14 | 컨설턴트 strategy 프롬프트에 최상급·효능 표현 금지 지침 1줄 추가 | 법률 규제 노드 없이 톤 문제를 LLM 모델 API 호출 0회·노드 0개로 방어. 기본 챗봇 copy_gen에 이미 있는 문장 재사용 | 노드 추가 / 미조치 |
| D-160 | 8/14 | check_regulation 대안은 message 문장에 포함해 전달, law·alternative는 내부 상태·평가용으로만 유지 | 서비스 BlockedResult가 4개 필드만 정의 + extra="ignore"(D-059)라 별도 필드가 에러 없이 버려짐. 골든 "대안 제시율"은 모델 레벨 측정이라 통과해 문제가 안 드러남 | 서비스 계약에 필드 추가 / 현행 방치 |
| D-161 | 8/14 | 규제 warn 상한 초과는 status="blocked" → 크레딧 전액 롤백 (§6.2 표 정정) | §6.2 "차감 유지"와 §7 "blocked면 롤백"이 정면 충돌. 사용자가 카피 0개를 받으므로 D-020 기준으로도 롤백 | 차감 유지 |
| D-162 | 8/14 | 계약서에 reason 코드 7종 목록 신설(§12.3) — 값 목록은 검증 계약서가 관리 | v0.3은 BlockedResult.reason을 자유 문자열로 두어 프론트가 화면 분기 기준을 알 수 없음. content_policy는 최상위가 아니라 ProposalError.reason임을 함께 명시 | v0.3에 위임 / 자유 문자열 유지 |
| D-163 | 8/14 | Model status(ok·blocked·error) / Generation status / HTTP status 3종 구분을 계약서 §12.1에 명시 | v0.3 §7에만 있어 모델 담당자가 혼동할 수 있음. 모델 노드는 Model status만 세팅 | v0.3 참조로 갈음 |
| D-164 | 8/14 | reask는 왕복 시 크레딧 관련 과금 구조임을 §7에 명시 — 후속 요청은 새 Idempotency-Key로 재차감 | v0.3 "과금 미완료"와 계약서 "롤백"이 같은 말인데 표현이 달라 혼동. reask 남발이 곧 사용자 크레딧 소모(기본 챗봇 D3 과잉 reask 사례) | 표현 차이 방치 |
| D-165 | 8/14 | 스모크 테스트에 masked_text 반환·alternative의 message 포함 검사 추가 | "대안이 조용히 사라지는" 유형은 런타임에 무음이라 CI로만 잡힌다 | 육안 확인 |
| D-166 | 8/14 | v0.3 문서의 크레딧 반전 잔재 4곳(§4.6·§6.3·§12.1·§13.1) 정정 요청 | 코드·§4.5·§10.4·§11.1·S-18은 D-057로 정정됐으나 문서 잔재가 남음. §12.1은 D1 완료 판정 기준이라 코드 역행 위험 | 방치 |
| D-167 | 8/18 | 골든 문항의 input은 부분 입력 — question·user_id·store는 평가기가 주입(models/shared/eval_fixtures.py) | v1.0은 전 문항에 필수 user_id가 없고 R-는 store도 없어 ModelRequest 검증 실패 → 평가기가 사용 불가. 완전 저장 방식은 공통값을 60회 반복해 유지보수 불가 | 문항마다 완전한 ModelRequest 저장 |
| D-168 | 8/18 | tests/eval/test_golden_dataset_schema.py를 CI에 추가(조립·개수·중복·fixture 검사) | 형식 오류를 60문항 완성 후 발견하면 전부 재작성. 문항 작성 중 매 PR마다 잡히게 함 | 검수 시 육안 확인 |
| D-169 | 8/18 | 컨설턴트 문항에 market_fixture 고정, 평가 중 외부 API 호출 금지 | 실시간 상권 데이터 의존 시 데이터 변동·API 장애로 점수가 흔들려 튜닝 효과 증명 불가. 업종코드 교정(D-041) 후 이전 측정과 비교 불가 문제도 해소 | 실시간 API 호출 유지 |
| D-170 | 8/18 | 환각 검증 = reasons 내 숫자의 allowed_numbers 화이트리스트 대조(규칙 기반), rubric의 환각_여부 항목 삭제 | must_contain_number는 숫자 1개만 있으면 통과해 근거 없는 수치를 못 잡음. LLM Judge는 상권 실제값을 몰라 환각 판단 근거가 없음. 규칙 기반이면 LLM 0회·재현 100% | LLM Judge에 위임 |
| D-171 | 8/18 | Hit Rate@5·MRR은 shared_data/retrieval_eval.json 별도 평가셋으로 분리, [SHOULD] 강등 | 정답 문서 ID·기준 컨텍스트가 스키마에 없어 계산 불가. 벤치마크 RAG 자체가 미착수(P-014). 8/18까지 문서 ID 미부여 시 보고서에서 제외 | golden_dataset에 필드 추가 / 지표 유지 |
| D-172 | 8/18 | Faithfulness 기준 컨텍스트는 문항에 기재하지 않고 런타임 state["context"]를 캡처해 결과 파일에 저장 | 파이프라인 변경 시 60문항을 고쳐야 함. 컨설턴트는 market_fixture가 곧 기준 컨텍스트 | 문항에 reference_context 기재 |
| D-173 | 8/18 | §10에 스크립트 구현 상태 표기 + DoD 4종(문항 수 검증·결과 파일 생성·원본 응답 저장·외부 API 미호출) | 동작하지 않는 명령이 문서에 있으면 담당자가 자기 환경 문제로 오인해 시간을 버림 | 명령만 기재 |
| D-174 | 8/18 | 거부 정확도는 test_contract.py가 아니라 models/shared/eval/eval_refusal.py로 측정 | test_contract.py는 반환 형식만 보는 스모크 테스트이고 골든 데이터셋을 읽지 않음 | 기존 명령 유지 |
| D-175 | 8/18 | B-004를 blog → banner 문항으로 교체 | platform이 instagram·banner 2종 확정(D-083). blog 문항은 요청 자체가 422라 실행 불가 | blog 복원 |
| D-176 | 8/18 | 일정표 요일 정정(8/19 수·8/20 목·8/21 금) + 0단계(배선) 신설, 파일럿 8/14 → 8/18 | 파일럿 마감이 이미 경과. 조립 규칙 없이 문항을 쓰면 평가기가 못 쓰므로 그릇을 먼저 만든다 | 기존 일정 유지 |
| D-177 | 8/18 | expected.action ↔ 모델 응답 매핑표 신설(§4.6), must_have_fields에 title 추가 | 모델은 성공 시 status="ok"를 반환하고 action은 blocked일 때만 존재 — 평가기가 무엇과 비교할지 정의되지 않았음. title은 계약상 빈 문자열 불가 필수 | 평가기 구현자 재량 |
| D-178 | 8/18 | R- 문항은 measured_at="function" — 서비스 응답이 아니라 검증 함수 반환 dict를 직접 검사 | alternative·law가 서비스 BlockedResult에 실리지 않음(D-160). 응답 계층에서 측정하면 대안 제시율이 항상 0이 됨. alternative_in_message로 D-160 이행도 함께 확인 | 서비스 응답 기준 측정 |
| D-179 | 8/18 | 컨설턴트 strategy 노드가 title 을 함께 반환 (title 만 폴백 허용) | ConsultantModelResult.title 이 min_length=1 필수이고 Contract §6.1은 ModelResult 계약 — 현재 mock_chatbot 이 합성해 통과 중이라 D7 교체 시 ValidationError→502. 기본 챗봇은 channel_format 이 생성해 비대칭. 기존 JSON에 필드 1개 추가라 호출 0회 | 서비스가 합성 / GraphState에 별도 노드 추가 |
| D-180 | 8/18 | 검증 함수 4종 실구현 8/18 내 완료 — PM 블로커 해소 (D-139 재확인) | D5 점검에서 4종 모두 D1 pass 스텁 확인. 두 챗봇 보안 노드가 차단하지 않고, 골든 R- 15문항 평가 불가, 발표 안전성 섹션 공백 | 8/19로 재연기 |
| D-181 | 8/18 | 스프린트 종료 시 각자 decisions.md 대비 자기 코드 30분 점검을 팀 규칙화 | D5 섹션 3에서 결정 미반영 6건 + Codex 4건 발견. 배포 환경 캐시 테이블 미생성(D-061)은 에러 없이 조용히 실패해 시연에서 드러나지 않았을 것. 크레딧 반전·sources 누락도 동일 유형 | 개별 판단에 위임 |
| D-182 | 8/18 | industry_code_map.json 을 상위 20개 업종으로 확장 | business_type 이 자유 문자열이라 "카페" 외 전 업종이 텍스트 매칭 폴백 — 강남역에서 16 vs 177(11배) 오차가 확인된 경로. 시연 Q&A에서 업종 변경 시 무너짐 | 카페만 유지 / 전체 247종 매핑 |
| D-183 | 8/18 | 회원가입 business_type 드롭다운 제한 검토 (서비스 담당, D8) | 매핑에 없는 업종을 입력받아 부정확한 수치를 주는 것보다 입력을 제한하는 편이 안전. Contract §4.2 자유 문자열 변경 필요(D-046 절차) | 자유 문자열 유지 |
| D-184 | 8/18 | 비용·한도가 있는 외부 API 신규 도입은 전민재 PM 승인 후 착수 + decisions.md 기록 필수 | search_ad_api 는 SDP 범위 밖 자체 확장이었으나 사전 공유·부분 성공 설계로 이번 건은 승인. 기록이 없으면 발표에서 데이터 출처를 설명할 근거가 없음 | 담당자 재량 |
| D-185 | 8/18 | search_ad_api(네이버 검색광고) 도입 승인 — related 필드 실데이터 확보 | repo_contract.md 가 related: list[str] 을 이미 계약으로 고정했으나 채울 API가 SDP에 없었음. 실패 시 빈 리스트 정규화로 부분 성공 보장 | 미도입(related 빈 배열 유지) |
| D-186 | 8/18 | 타 담당 관리 파일 수정 시 PR 본문 명시 + 원 관리자 리뷰 요청 필수 | cache/db.py(전민재 PM 초안)를 확인 없이 수정 — 결과는 옳았으나 관리권 경계가 무너지면 D7 통합에서 충돌. 이번 건은 승인 | 자유 수정 / 수정 금지 |
| D-187 | 8/18 | D7/D8 대기 중 계약 정합성 3건(title·blocked 형식·sources 최소 1개)을 D9보다 먼저 처리 | 서비스 D4가 곧 완료되어 D7이 풀림. 컨텍스트 전환 비용을 줄이고 즉시 연동 가능한 상태로 대기 | D9 전면 선행 |
| D-188 | 8/18 | get_trend() 의 industry 인자는 의미 정의 또는 제거 후 repo_contract.md 갱신 | 계약서에 시그니처만 있고 의미가 없어 두 챗봇이 값을 넘기지만 아무 효과가 없는 죽은 파라미터 | 현행 유지 |
| D-189 | 8/18 | weather 가 항상 None 임을 기본 챗봇 담당에게 통보 | trend_for_copy 가 요약 문장에 weather 를 포함하도록 구현돼 있어 해당 절이 영구 미출력. 계약 위반은 아니나 코드가 오해를 유발 | 통보 없이 진행 |
| D-190 | 8/18 | few-shot 예시 키워드는 테스트·평가 데이터와 겹치지 않게 작성 | 예시와 실제 입력이 겹치면 LLM이 예시를 그대로 베낌(D6에서 "아이스아메리카노"→"브런치 세트" 교체로 방지). 골든 데이터셋 rubric·예시에도 동일 적용 | 임의 선정 |
| D-191 | 8/18 | 컨설턴트 골든 문항의 market_fixture 는 D5 실측값(강남역 카페 177곳/전체 6,691곳) 기준 | 업종코드 교정(D-041~043) 후 값이므로 재교정 없이 안정적. golden_dataset v1.1 §4.4 필수 요건 충족 | 교정 전 값 사용 |
| D-192 | 8/18 | 계약서 예시 응답은 현재 실제 반환값과 일치해야 하며, 미구현 필드는 예시에서도 null + "(미구현)" 표기 | repo_contract.md 예시가 weather에 값을 채워 보여줘 기본 챗봇이 그대로 mock을 만듦 → 단위 테스트는 통과하나 실제로는 해당 절이 영구 미출력. title(D-179)과 동일 구조 | 필드 표의 "선택" 표기로 갈음 |
| D-193 | 8/18 | trend_for_copy의 weather 분기 제거(또는 미구현 주석 명시), 날씨 연동은 D9 [SHOULD] | get_trend()가 weather를 채우지 않아 죽은 코드 상태. 남겨두면 이후 담당자가 "이미 구현됨"으로 오인. add_sw_req_spec 5)의 날씨 기반 카피는 백로그로 이관 | 즉시 날씨 API 연동 / 현행 방치 |
| D-194 | 8/18 | 날씨 연동 시 get_trend()에 포함하지 않고 별도 함수·별도 TTL로 분리 | 트렌드 캐시 TTL이 7일이라 같은 캐시에 묶으면 일주일 전 날씨로 카피를 생성 | get_trend()에 통합 |
| D-195 | 8/18 | 다른 담당자가 구현한 함수를 mock으로 대체할 때 실제 조회 함수의 현재 반환값과 대조 후 mock 작성 | mock이 실제보다 관대하면 테스트는 초록불인데 운영에서 실제 기능처럼 실행 불가. 기본 챗봇 단위 테스트는 weather 있음·E2E fake는 None이라 양쪽 다 불일치를 못 잡았음 | 계약서 예시 기준으로만 작성 |
| D-196 | 8/18 | regulation_node는 판정을 항목에 붙이지 않고 validation["regulation"]에만 기록 | {**c, "regulation": ...} 가 ranked_copies에 내부 키를 남김. image_review의 clip_score와 함께 누적되는 구조라, channel_format 화이트리스트가 유일한 방벽. 중첩 strict(P-018) 상태에서 화이트리스트 확장 시 502 | 화이트리스트 의존 유지 |
| D-197 | 8/18 | 법률 규제 차단 슬롯은 제자리 치환 — passed+blocked+failed 방식 금지 | 차단 항목이 배열 뒤로 밀려 ranking_node의 점수순 정렬이 무너짐. 사용자 화면에서 2번 카드가 3번으로 이동. 현재 테스트가 2개짜리라 미검출 | 뒤에 붙이기 유지 |
| D-198 | 8/18 | 이미지 검수 정책: 이미지 없음·CLIP 저점수는 pass, 디코딩 전부 실패만 reject (D-075 이행) | CLIP은 영어 전용이라 한국어 카피 점수가 무의미(P-015), FR-13b도 CLIP을 개발용 지표로 규정. 요청당 이미지 6장 → 3장으로 감소 | 저점수도 재생성 |
| D-199 | 8/18 | classify_llm_error는 models/basic/llm_errors.py 관리(shared 아님) | shared는 전민재 PM 관리 영역이고 오류 분류는 챗봇별 응답 정책. 계약 enum 4종(timeout·rate_limit·provider_error·unknown) 준수는 유지(D-073) | shared에 편입 |
| D-200 | 8/18 | route_after_ranking 추가 승인 — ranking LLM 오류 시 조기 종료 | error 상태로 regulation에 진입하면 ranked_copies 부재로 KeyError. 담당자 자체 판단 개선분 | 라우터 미추가 |
| D-201 | 8/18 | trend_for_copy는 question 원문이 아닌 question_analysis의 keyword 사용 (D-079 기본 챗봇 이행) | 원문 사용 시 캐시 키가 매번 달라 적중률 0% → NAVER 월 5만 건 한도 직격. 문장 검색은 트렌드 결과 자체가 무의미. 컨설턴트는 D5에 이미 반영 | 원문 유지 |
| D-202 | 8/18 | LLM 응답 json.loads 실패도 예외 처리 대상 — parse_failed 슬롯으로 전환 | call_llm 예외는 잡지만 파싱 실패는 무방비. json_mode로 확률은 낮으나 발생 시 그래프 전체 중단 | 현행 유지 |
| D-203 | 8/18 | 노드 단위 테스트는 실제 조회 함수의 현재 반환값과 대조 후 mock 작성 (D-195 기본 챗봇 이행) | test_trend_for_copy가 weather에 값이 있는 mock을 사용 — 실제 get_trend는 항상 None이라 해당 분기가 운영에서 미실행 | 계약서 예시 기준 |
| D-204 | 8/18 | 컨설턴트 응답 조립 레이어 신설 — models/consult/main.py::run()·assemble_response() | D1+D2에서 "응답 시 변환"으로 정하고 D4 구현 예정이었으나 전민재 PM 범위 설정 누락으로 미구현. state["result"]가 평면(summary·actions·reasons)인데 계약은 strategy 중첩이라 D7 교체 시 ValidationError→502 | 서비스가 state를 직접 조립 |
| D-205 | 8/18 | 모델→서비스 경계는 dict in / dict out, 모델은 backend를 import하지 않는다 | Contract §2.2(Model은 ModelResult를 반환). 서비스가 state 내부 구조를 알면 파이프라인 변경 시마다 서비스 코드 수정 필요. backend import는 배포 단위 분리(D-031) 위반 | pydantic 객체 직접 전달 |
| D-206 | 8/18 | 모델은 동기 run()을 제공하고 서비스가 asyncio.to_thread로 감싼다 | LangGraph 노드가 전부 동기 — async 안에서 직접 호출하면 최대 60초 이벤트 루프 정지. D-121(await 전 트랜잭션 종료)과 짝 | 모델을 async로 재작성 |
| D-207 | 8/18 | 그래프 예외는 run() 진입점 1곳에서 잡아 ErrorResult로 변환 (컨설턴트) | strategy의 "형식 오류 즉시 실패" 원칙을 유지하면서 계약도 지킴. 노드마다 try/except를 넣는 기본 챗봇 방식(D-199)과 다르나 결과는 동일 | 노드별 예외 처리로 통일 |
| D-208 | 8/18 | classify_llm_error 함수를 models/shared/llm_errors.py로 이관 (D-199 변경) | classify_llm_error 함수를 기존에는 기본 챗봇만 사용했으나 컨설턴트 챗봇 run()도 필요해 기본 챗봇, 컨설턴트 챗봇 2개 다 공통으로 사용함. 매핑 대상(ErrorResult.reason 4종)은 챗봇 정책이 아니라 서비스 계약 — directory_structure §7.3 통합 기준 해당 | basic 전용 유지 / 컨설턴트가 별도 복사 |
| D-209 | 8/18 | title·sources·suggested_chips는 조립 단계에서 최종 폴백 (실패시키지 않음) | title은 이력 목록 라벨, sources·chips는 계약 최소 요건. 여기서 실패시키면 정상 생성된 전략을 부수적 필드 때문에 버리게 됨. summary·actions·reasons는 기존대로 엄격 유지 | 전 필드 엄격 검증 |
| D-210 | 8/18 | 모델 응답 조립 결과를 서비스 스키마로 검증하는 계약 테스트를 각 챗봇에 필수 배치 | 노드 단위 테스트가 전부 초록불이어도 서비스에 붙이면 502가 나는 구조(3안 개수·title·중첩 구조). backend import는 테스트 파일에서만 허용 | D7 통합 시 수동 확인 |
| D-211 | 8/18 | D7 계약 정합성 항목 재정의 — sources는 D6에서 완료, blocked은 "형식 확인"이 아니라 "레이어 신설" | 전민재 PM 지시 문구가 부정확해 담당자가 존재하지 않는 코드를 찾는 데 시간을 씀. 요청 시 "확인"과 "신설"을 구분해 표기 | 기존 표현 유지 |
| D-212 | 8/18 | 기본 챗봇 계약 테스트는 컨설턴트 복사가 아닌 별도 작성 — proposals 3개 고정·슬롯 불변조건·내부 키 누출 3항목 추가 (P-037 이행) | 두 챗봇 계약이 다름(Basic은 proposals 3개 고정·suggested_chips 빈 배열 필수, Consultant는 strategy 중첩·chips 정확히 3개). BasicProposal.validate_slot_state가 copy·image_b64·error 조합을 검사하는데 channel_format은 그 정합성을 확인하지 않음 | 컨설턴트 테스트 복사 |
| D-213 | 8/18 | channel_format의 title에 폴백 추가 — question이 공백이면 "{가게명} 광고 제안" | question_analysis가 rewritten_question을 빈 문자열로 반환하면 state["question"]이 ""가 되고 title[:30]도 "" → min_length=1 위반 502. parsed.get()은 키가 있으면 빈 문자열도 채택 | question[:30] 유지 |
| D-214 | 8/18 | assemble_response는 issues의 reason을 ErrorResult enum 4종으로 매핑, 밖이면 unknown | copy_gen이 넣는 copy_generation_failed가 enum 밖이라 그대로 내보내면 502(D-073 미이행분). 내부 reason과 계약 reason을 분리 | 내부 reason 그대로 전달 |
| D-215 | 8/18 | blocked 응답의 message는 빈 문자열 금지 — 폴백 문구 적용 | regulation_node가 blocked.get("message","")로 빈 문자열을 넣을 수 있는데 BlockedResult.message는 min_length=1 | 빈 문자열 허용 |
| D-216 | 8/18 | proposals 항목의 허용 키는 copy·image_b64·error 3종으로 고정, 회귀 테스트로 잠금 | score·clip_score·regulation이 내부에서 누적되는 구조(D-196). 중첩 strict(P-018)에서 누출 시 즉시 502이며 화이트리스트가 유일한 방벽 | 화이트리스트 신뢰 |
| D-217 | 8/18 | 계약 테스트에서 빨간불이 나오는 것을 정상 상태로 간주 — 프로덕션 수정 후 초록불 확인 | D7 통합 당일에 발견할 502를 사전 노출하는 것이 테스트 목적. 초록불을 맞추려 테스트를 완화하지 않는다 | 통과하도록 테스트 조정 |
| D-218 | 8/18 | 골든 문항은 프롬프트 few-shot 예시와 수치·키워드가 겹치면 안 된다 (평가 오염 차단) | 겹치면 LLM이 데이터를 안 읽고 예시를 베껴도 allowed_numbers 검증과 LLM Judge를 모두 통과 — 환각률 0%라는 거짓 결과. repo_contract 예시(12곳·43곳·55m)가 strategy.py few-shot과 이미 겹침 | 겹침 허용 / 육안 대조 |
| D-219 | 8/18 | 겹침 여부를 CI가 자동 검사 — tests/eval/test_prompt_contamination.py | 60문항 × 프롬프트 2종을 사람이 매번 대조할 수 없음. FEWSHOT_TERMS·FEWSHOT_NUMBERS 상수 선언 자체도 강제(빈 리스트도 명시) | 검수 시 육안 확인 |
| D-220 | 8/18 | 겹침 발견 시 문항이 아니라 프롬프트 예시를 바꾼다 | 골든 문항은 시연 시나리오·스토리보드와 묶여 있어 바꾸면 측정 대상이 달라짐. few-shot은 보조 장치라 교체 자유. D6 컨설턴트 조치("아이스아메리카노"→"브런치 세트")와 동일 방향 | 문항을 바꾼다 |
| D-221 | 8/18 | market_fixture에 fixture_version·captured_at 필수화, 결과 파일에도 기록 | 교정 전(12곳)/후(177곳) fixture로 측정한 점수를 비교하면 데이터 변동을 모델 개선으로 착각. v1.1이 fixture를 고정했으나 fixture 자체가 바뀔 수 있다는 점을 누락 | 버전 없이 사용 |
| D-222 | 8/18 | "데이터 정확도" 지표 축 신설 — 업종 매핑 커버리지·정확 판정 비율 (LLM 호출 0회) | 기존 지표는 전부 모델 출력 기준이라, 모델을 안 바꾸고 입력을 고친 개선(16→177)을 측정할 칸이 없음. LLM Judge는 "숫자가 있는가"만 보고 "그 숫자가 맞는가"는 못 봄 | 모델 출력 지표만 유지 |
| D-223 | 8/18 | 컨설턴트 fixture 표준값을 v2-industry-code(강남역 177곳/6,691곳)로 확정, v1-text-match 사용 금지 | v1.1 예시(105곳)는 추정치였고 D5 실측은 177곳. 교정 전 값(12·16곳)은 부정확한 데다 few-shot과 겹쳐 이중으로 부적합 | v1.1 예시값 유지 |
| D-224 | 8/18 | 개선 사례를 docs/improvements.md에 4단계(가설→원인규명→개선→재측정)로 누적, 첫 사례는 업종코드 필터 | 평가항목 "성능 개선을 위해 다양한 시도"에 직접 대응. 결정 ID를 인용해 추적 가능하게 함. 실패한 시도도 기록 | 발표 직전 일괄 정리 |
| D-225 | 8/18 | tests/eval/test_golden_dataset_schema.py 코드 블록 복원 (v1.2 개정 중 누락) | §9 체크리스트·§10.1 상태표·§10.3 명령 세 곳이 참조하는데 코드만 빠짐. PR #94 지적 1번(user_id 누락으로 ModelRequest 검증 실패)을 막는 장치라 없으면 같은 사고 재발 | 오염 검사만 유지 |
| D-226 | 8/18 | 데이터셋 검증은 스키마 → 오염 순서로 실행 | 조립도 안 되는 문항의 겹침을 검사하는 것은 순서가 뒤바뀐 것. 스키마 통과가 오염 검사의 전제 | 순서 무관 |
| D-227 | 8/18 | 스키마 테스트에 검사 4종 추가 — id 접두사·area 일치, input의 user_id·question 중복 금지, fixture_version 고정, allowed_numbers의 fixture 파생 가능성 | allowed_numbers에 fixture에 없는 숫자를 넣으면 환각 검증이 무력화됨(D-170 우회 경로). 나머지 3종은 §4.2.1·§4.4 규칙을 코드로 강제 | v1.1 검사 3종 유지 |
| D-228 | 8/18 | 문서에 실린 코드 블록과 §10.1 구현 상태 표를 양방향으로 일치시킨다 | 표에는 있는데 코드가 없거나 그 반대면 담당자가 찾지 못함. cache/db.py·sources·title과 동일한 "참조는 남았는데 실체가 없음" 유형이 문서에서 재현됨 | 표만 관리 |
| D-229 | 8/18 | 코드 주석의 결정 ID는 decisions.md와 대조 후 커밋, PR 단위로 grep 전체 스캔 | search_ad_api.py가 D-179(title 반환)를 참조하나 실제는 D-185. 잘못된 ID는 역추적 시 엉뚱한 결정으로 안내해 없느니만 못함 | 주석 ID 자유 기재 |
| D-230 | 8/18 | repo_contract.md의 weather 예시를 null + "(현재 미구현)"로 정정 (D-192 이행) | trend_api.fetch()가 weather=None을 하드코딩하는데 계약서 예시는 값이 채워져 있음. 동일 원인으로 기본 챗봇 trend_for_copy에 죽은 분기가 이미 생김(D-193) | 예시 유지 |
| D-231 | 8/18 | repo_contract.md의 market 예시 수치를 실측값 기준으로 정정하거나 "문항 복사 금지" 주석 명시 | D-218(골든 문항의 few-shot 겹침 금지)에서 12곳·43곳·55m가 오염 대상인데 계약서가 그 값을 제시 중 | 현행 유지 |
| D-232 | 8/18 | get_trend()의 industry 인자는 제거 확정, 실행은 D8 정리 PR (D-188 결론) | 트렌드는 최종 결과를 통째 캐싱하므로 industry를 캐시 키에 넣으면 같은 검색어가 업종별로 중복 캐싱돼 적중률 하락. 검색어 트렌드 API 자체가 업종을 받지 않음. 즉시 제거는 기본 챗봇 동시 수정이 필요해 D6·D7과 충돌 | 즉시 제거 / 의미 부여 |
| D-233 | 8/18 | trend_repo._write_cache에 upsert 적용 (D-053 트렌드 확장) | market_repo만 upsert 적용됨. 반복 조회 시 행 누적 + 동일 payload TTL 미갱신 버그가 트렌드에서 재발 | INSERT 유지 |
| D-234 | 8/18 | industry_breakdown은 원본 1000곳 한계가 있으므로 전략 프롬프트에서 제외 검토 | same_industry_count는 업종코드로 정확해졌으나 breakdown은 여전히 부분 집계 — 강남역 기준 15%만 반영된 분포가 LLM 근거로 사용됨. 16→177과 동일 문제의 잔여분 | 현행 유지(TODO만) |
| D-235 | 8/18 | 캐시 관련 상수(_MAX_RELATED_KEYWORDS 등)는 models/consult/config.py로 집약 | TTL 상수는 이미 이관됨. 모듈 하드코딩이 남으면 조정 지점이 분산(D-047 취지) | 모듈 내 유지 |
| D-236 | 8/18 | cache/db.py의 create_all 예외는 로그만 남기고 삼킨다 (승인) | 예외가 import 시점에 올라가면 market_repo·trend_repo import가 통째로 실패해 "DB 장애 시 실시간 API 폴백" 원칙 자체가 무력화. 담당자가 연결 불가 DB로 재현 후 회귀 테스트 추가 | 예외 전파 |
| D-237 | 8/18 | 구버전 캐시 DB 스키마는 ALTER TABLE 경량 보정으로 처리 (Alembic 미도입 D-067과 일관) | create_all()은 기존 테이블에 컬럼을 추가하지 않아 industry_code 누락 시 캐시 전체가 no such column으로 실패 | Alembic 도입 / 수동 재생성 |
| D-238 | 8/18 | 골든 문항의 fixture는 그 질문이 운영에서 실제로 만들어낼 상태와 일치해야 한다 | 평가 조건이 운영과 다르면 측정 점수가 운영 품질을 예측하지 못하고 튜닝이 "평가에서만" 효과를 낸다. trend=None 고정은 keyword 없는 질문에서는 운영과 일치하지만 특정 메뉴가 있는 질문에서는 불일치 | trend 전체 None 고정 / 전체 fixture 추가 |
| D-239 | 8/18 | C- 문항에 input.trend_fixture 추가, 값이 없으면 명시적 null (생략 금지) | 생략과 "없는 게 맞음"을 구분해야 CI가 누락을 잡을 수 있다. market_fixture와 동일하게 fixture_version·captured_at 필수 | 필요한 문항에만 키 추가 |
| D-240 | 8/18 | expected.trend_used(bool) 신설 — 경로 재현성 검증 + "경로 일치율" 지표 | keyword 추출이 LLM 산출물(temperature 0.3)이라 fixture를 고정해도 호출 여부가 실행마다 달라져 점수가 흔들림. 불일치는 실패가 아니라 질문 분석 노드 안정성 지표로 집계 | 데이터만 고정 |
| D-241 | 8/18 | trend_fixture 도입 전에는 C- 본 평가를 실행하지 않는다 (파일럿만 허용) | 첫 측정이 baseline이 되어 이후 튜닝 비교가 조건 변경과 뒤섞임(D-221과 동일 구조). LLM Judge 유료라 폐기용 1회분 비용도 발생 | None 조건으로 1차 평가 선행 |
| D-242 | 8/18 | trend_fixture.weather는 항상 null | get_trend()가 weather를 반환하지 않음(D-230). 값을 넣으면 운영에 존재하지 않는 조건을 평가하게 됨 | 계약서 예시대로 값 기입 |
| D-243 | 8/18 | trend 도입으로 allowed_numbers는 변경하지 않는다 — 트렌드 필드에 수치가 없음 | keyword·direction·related 모두 텍스트. 텍스트 근거 검증이 필요해지면 allowed_terms를 별도 신설(현재 불필요) | allowed_numbers 확장 |
| D-244 | 8/18 | fixture 주입은 eval 스크립트의 patch에서만 수행, eval_fixtures.py는 수정하지 않는다 | build_model_request()가 알려진 키만 담아 trend_fixture를 자동 무시. 담당자 예상보다 작업량이 작음을 확인 | eval_fixtures.py 확장 |
| D-245 | 8/18 | C- 문항 수는 20 유지. 초과 작성분은 notes="extended" 표시 후 [SHOULD] 확장셋으로 분리 | §10.2 스키마 테스트가 consult:20을 assert하며 45면 즉시 실패. LLM Judge 비용 2.25배로 $30 한도 압박. 작성분을 버리지 않고 보존 | 45로 상향 / 초과분 폐기 |
| D-246 | 8/18 | 경로 일치 판정은 context["trend"] 가 아니라 question_analysis.keyword 를 기준으로 한다 | trend 가 None 이 되는 경로가 둘("keyword 없음"·"keyword 있으나 fixture null")이라, trend 로 판정하면 trend_used=false 문항에서 LLM이 keyword를 뽑아버린 불일치를 놓친다 | context["trend"] 기준 |
| D-247 | 8/18 | check_trend_path 는 bool 이 아니라 dict 반환 — keyword·trend_in_context 동봉 | 불일치 방향(과추출/미추출)에 따라 조치가 다르고, trend_in_context 는 fixture 주입 실패(하네스 버그)를 모델 성능 문제와 구분해준다 | bool 반환 |
| D-248 | 8/18 | must_not_include_sources 필드는 만들지 않고 trend_used 에서 평가기가 유도 | 필드를 늘리면 작성자 실수 지점만 늘어난다. trend_used=false → sources 에 "트렌드" 없음은 기계적으로 도출 가능 | 별도 필드 신설 |
| D-249 | 8/18 | trend_fixture 여부는 type 이 아니라 질문 문장의 특정 메뉴·상품명 유무로 판단 | type=strategy 안에서도 갈린다("어떻게 홍보?"=null / "아메리카노 프로모션?"=값). type 일괄 적용 시 절반이 어긋남 | type 기준 일괄 적용 |
| D-250 | 8/18 | 경로 일치율 목표 90% — 미달 시 LLM Judge 점수 해석을 보류 | 경로가 흔들리면 프롬프트 구성이 달라져 점수 비교 자체가 성립하지 않는다 | 목표치 미설정 |
| D-251 | 8/19 | LLM Judge 모델을 OPENAI_JUDGE_MODEL 로 구조 분리, call_llm()에 선택적 model 인자 추가 | D-051(LLM 모델 A/B 후 확정)이 현재 구조로는 불가능 — OPENAI_MODEL 변경 시 생성·채점이 동시에 바뀌어 점수 차이의 원인을 분리할 수 없다. fixture_version(D-221)·trend_used(D-240)와 동일한 "비교하려면 나머지를 고정" 원칙 | 공통 모델 유지 |
| D-252 | 8/19 | OPENAI_JUDGE_MODEL 기본값은 OPENAI_MODEL 과 동일, 상위 모델 전환은 파일럿 !usage 확인 후 | Judge 대상이 45문항 × 전후 2회 = 90회 이상. $30 한도에 basic·refusal 측정과 D10 재측정이 남아 있어 구조 분리와 비용 발생을 분리한다 | 즉시 상위 모델 적용 |
| D-253 | 8/19 | 결과 파일의 model 을 generation_model 로 개명하고 judge_model 과 병기 | judge_model 단독으로는 "무엇을 채점했는지" 알 수 없어 점수 해석 불가. model 이라는 이름도 judge_model 옆에서 모호해짐 | judge_model 만 추가 |
| D-254 | 8/19 | generation_model 과 judge_model 을 동시에 바꾼 두 결과는 비교하지 않는다 | 한쪽만 다르면 각각 "생성 성능 차이"·"채점자 성향 차이"로 해석되지만, 둘 다 다르면 원인 분리 불가. fixture_version 규칙(D-221)의 확장 | 비교 허용 |
| D-255 | 8/19 | Judge 호출에는 deadline 을 전달하지 않는다 | D-144 데드라인은 그래프 실행 예산이고 Judge 는 그래프 밖 평가 코드 — 전달 시 평가 배치가 중도 중단된다 | 동일 deadline 적용 |
| D-256 | 8/19 | config 의 JUDGE 모델은 getenv(...) or OPENAI_MODEL 형태로 읽는다 | .env.example 에 빈 값으로 배포되므로 getenv 기본값이 발동하지 않고 빈 문자열이 모델명으로 전달된다 | getenv 기본값 인자 사용 |
| D-257 | 8/19 | get_total_tokens() 를 모델별 집계로 변경(인자 생략 시 전체 합계) | 생성·채점 토큰이 합산되면 D-092(예산 모니터링) 목적을 달성할 수 없다. 기존 호출부는 무인자 호출이라 하위 호환 유지 | 단일 카운터 유지 |
| D-258 | 8/19 | judge_model 은 파일럿(8/18)에 확정하고 본 평가(8/20) 이후 고정 | Judge 변경은 fixture 변경과 동일하게 baseline 을 무효화 — 본 평가 중 변경 시 기측정 점수 전량 폐기 | 상시 변경 허용 |
| D-259 | 8/19 | §11에 비교 가능성 판정 표·3단계 확인 절차 신설 — 조건이 2개 이상 다르면 비교 금지 | §10.4는 기록 규칙이고 §11은 해석 규칙 — 잘못된 비교는 발표 자료 작성 시점(§11)에 발생한다. 기록 필드만 있고 해석 규칙이 없으면 아무도 안 보고 비교한다 | §10.4 기록 규칙으로 갈음 |
| D-260 | 8/19 | 비교 규칙은 "generation·judge 동시 변경 금지"가 아니라 "달라진 조건 개수"로 일반화 | 금지문 하나만 두면 fixture_version·dataset_version 이 섞였을 때 못 잡는다. 조건이 늘어도 규칙이 그대로 작동해야 한다 | 모델 조합만 명시 |
| D-261 | 8/19 | 비교표에는 "측정 조건" 블록과 "바꾼 것" 한 줄을 반드시 병기 | 숫자만 있으면 개선 노력이 아니라 우연으로 읽힌다. 평가항목 "성능 개선을 위해 다양한 시도"에 직결 | 지표 표만 기재 |
| D-262 | 8/19 | compare_reports.py 로 비교 가능성 자동 확인 (선택, 8/20) | 지표 10종 × 3영역 × 다회차가 쌓이면 육안 대조에서 누락 발생. 3단계 확인 절차만으로도 최소 요건은 충족 | 육안 확인만 |
| D-263 | 8/19 | §10.4 결과 파일 스키마와 DoD ⑤를 generation_model·judge_model 병기로 갱신, compare_reports.py 를 §10.1 상태표에 등재 | §11만 바꾸면 문서 내 필드명이 어긋난다. 문서에 실린 코드는 상태표에 등재해야 담당자가 찾을 수 있다(D-228) | §11만 수정 |
| D-264 | 8/19 | call_llm 은 model 을 resolved_model 로 한 번만 해석해 호출·집계에 동일 값 사용 | raw model(None)을 집계 키로 쓰면 KeyError 발생, 회피해도 모든 토큰이 None 키에 쌓여 모델별 집계(D-257)가 무의미해짐. 해석 지점이 둘이면 언제든 다시 어긋난다 | 집계 시점에 별도 해석 |
| D-265 | 8/19 | 누적 토큰 집계는 dict.get(k, 0) 사용, defaultdict 미사용 | defaultdict 는 읽기만 해도 키가 생성돼 오타 모델명이 집계에 유입됨. 쓰는 쪽에서만 명시적으로 초기값을 준다 | defaultdict(int) |
| D-266 | 8/19 | 상태 컨테이너 타입 변경(int→dict 등) 시 그 기능을 직접 검증하는 테스트를 같은 PR에 포함 | 실패한 4개는 다른 목적의 테스트가 부수적으로 걸린 것 — KeyError만 고치면 8개 전부 초록불인 채 집계가 망가진 상태로 머지됨. D-227 원칙 미이행 | 기존 테스트에 의존 |
| D-267 | 8/19 | reset_total_tokens() 추가 및 autouse fixture 에서 카운터 초기화 | 모델별 집계는 프로세스 전역이라 테스트 간 값이 누적돼 절대값 검증이 불가능. 싱글턴 클라이언트(D-088)와 같은 격리 원칙 | 델타 비교로만 검증 |
| D-268 | 8/19 | dict 변경만 하는 함수에서 global 선언 제거, 주석 처리된 옛 코드 삭제 | dict 는 재바인딩이 아니라 mutation 이라 global 이 불필요. 주석 처리된 구버전 코드는 다음 수정자에게 어느 쪽이 맞는지 혼란을 준다 | 현행 유지 |
| D-269 | 8/19 | 토큰 집계 갱신에 threading.Lock 적용 검토 — D7 실연동 시 결정 | D-206(asyncio.to_thread)으로 동시 요청이 여러 스레드에서 call_llm 을 타므로 get→set 사이 유실 가능. 예산 참고 수치라 심각도는 낮으나 3줄로 제거 가능 | 락 미적용 확정 |
| D-270 | 8/20 | 검증 함수 4종 구현 순서를 'LLM 호출 0회 함수 우선'으로 고정 — check_input → check_output → self_check → check_regulation 1단 → 2단 | 앞 세 함수는 순수 규칙이라 OPENAI_API_KEY·네트워크·$30 한도와 무관하게 하루 안에 완결된다. 4종 동시 착수하면 파이프라인이 깨졌을 때 원인이 4개로 분산되고, 외부 의존이 있는 법률 규제 검증의 장애가 나머지 3종의 진척까지 가린다. 계약서 §9 기준 실구현 마감(8/19)을 이미 넘긴 상태(D-142)라 원인 분리 비용을 더 지불할 여유가 없다 | 4종 동시 착수 |
| D-271 | 8/20 | 2단 RAG 판정 실패(키 미설정·타임아웃·JSON 파싱 실패·예산 소진) 시 1단 히트 조항의 허용 예시로 warn 을 구성해 반환(degrade). llm_judge.judge() 는 예외 대신 None 반환 | fail-open(pass)은 위험 문구를 그대로 내보내 검증 함수를 붙인 의미를 없애고, fail-closed(block)는 과잉 차단률을 폭증시켜 골든 R-011~R-015 를 전멸시킨다. 1단이 이미 근거 조항을 지목했으므로 legal_kb 의 허용 예시·대안 가이드만으로 law·reason·alternative 를 채울 수 있어 대안 제시율 100%가 장애 상황에서도 유지된다(실측: 2단 없이 위반 카피 25건 → warn 25건·대안 100%). judge 가 raise 하면 호출부가 degrade 할 기회를 잃고 파이프라인 전체가 status="error" 로 끝난다 | fail-open(pass) 또는 fail-closed(block) |
| D-272 | 8/20 | 1단 키워드 트리거·예외 사전을 legal_kb.md 의 **트리거** / **예외 표현** 섹션에서 자동 생성 — validation/patterns.py 에는 보안1·2 패턴만 유지 | 사전과 KB 가 다른 파일이면, KB 에만 조항을 추가했을 때 1단에서 걸리지 않아 2단이 볼 기회조차 없이 조용히 놓친다. 반대로 사전에만 넣으면 2단이 검색할 근거가 없어 LLM 모델이 pass 를 내거나 엉뚱한 법률 조문을 인용한다. 원본이 하나면 트리거 누락·허용 예시 누락을 build_legal_kb.py --check 가 CI 에서 잡는다(현재 36청크에서 트리거 184개·예외 53개 자동 생성). 계약서 §6.2.1 의 '사전에 예외를 계속 추가해도 끝이 없다'는 지적에 따라 1단은 recall 우선, 정밀도는 2단 담당으로 역할을 고정한다 | patterns.py 에 RISKY_HINTS 를 별도 관리 |
| D-273 | 8/20 | check_output 민감정보를 3티어로 분리 — 크리덴셜·시스템 프롬프트는 block, 주민번호·카드·계좌는 warn+마스킹, 전화·이메일은 CTA 문맥(문의·예약·주문 등)이면 pass. 정규식 순차 sub() 대신 스팬 선점 방식 적용, 주민번호는 날짜 검증·카드는 Luhn 체크섬 통과 시에만 마스킹. 계약서 §5.1 예시 수정을 §14 절차로 요청 | 연락처가 지워진 광고 문구는 소상공인이 쓸 수 없고, 식품표시광고법 제7조는 오히려 광고에 제품명·업소명 표기를 요구한다. 크리덴셜은 부분 노출도 사고라 마스킹으로 안전을 보장할 수 없어 유일한 block 대상이다. 정규식을 순서대로 sub() 하면 '010-1234-5678'이 계좌번호 패턴에 먼저 잡혀 전화번호 규칙이 실행조차 되지 않고, 검증 없는 정규식은 사업자등록번호(123-45-67890)까지 민감정보 마스킹 처리한다 — 실제로 초기 구현에서 두 건 모두 재현됐다. §10 스모크 테스트는 이미 action=="pass" 분기를 갖고 있어 코드 수정 없이 통과하므로 문서만 고치면 된다 | 연락처 일괄 민감정보 마스킹(계약서 §5.1 예시 그대로) |
| D-274 | 8/20 | generation_model=gpt-4o-mini 유지, judge_model=gpt-4.1-mini 로 명시 고정. .env 에 OPENAI_JUDGE_MODEL 을 직접 설정한다. G-02·G-10·P-046 종료 | config.py 의 OPENAI_JUDGE_MODEL 기본값이 OPENAI_MODEL 이라(D-252) 미설정 시 Judge 가 생성 모델을 따라간다 — 이 상태로 D-051 LLM 모델은 D5 A/B(3문항)를 돌리면 OPENAI_MODEL 을 바꾸는 순간 judge_model 도 함께 바뀌어 기준 문서 §11.2.2 의 "잘못된 비교"가 그대로 재현된다. 구조 분리(D-251)는 값을 박아야 완성된다. Judge 가 생성보다 상위 세대여야 자기 출력 선호 편향도 줄어든다. 기준 문서 §10.4·§11.1 예시가 이미 gpt-4.1-mini 다 | judge=gpt-4o-mini 유지(생성과 동일) / 즉시 최상위 모델 적용 |
| D-275 | 8/20 | call_llm 에 temperature 인자 추가, LLM_JUDGE_TEMPERATURE=0.0 신설. Judge 호출은 반드시 0 을 넘긴다. 구현은 `LLM_TEMPERATURE if temperature is None else temperature` | 기존 코드는 temperature=LLM_TEMPERATURE(0.3) 하드코딩이라 Judge 도 0.3 으로 돈다. 같은 응답을 두 번 채점해도 점수가 달라져 기준 문서 §1.4 "같은 입력에 같은 점수"가 깨지고, judge_model 을 아무리 잘 골라도 자[尺]가 흔들려 D-251 의 목적이 무너진다. `or` 를 쓰면 0.0 이 falsy 라 조용히 0.3 으로 되돌아간다 — D-264 와 동일 유형 | temperature 하드코딩 유지 / 채점 프롬프트로만 일관성 유도 |
| D-276 | 8/20 | Judge 파일럿은 "생성 1회로 응답 고정 → 동일 응답을 3회 채점"으로 설계. 통과 기준은 rubric 전 항목 3회 점수 편차 0 | 생성과 채점을 매번 새로 돌리면 점수 차이가 생성 분산(temperature 0.3) 때문인지 Judge 분산 때문인지 분리되지 않는다 — §11.2.2 "한 번에 하나만 바꾼다"와 같은 논리다. rubric 이 1~5 정수 척도이므로 temperature 0 에서는 편차 0 이 정상이며, 편차가 나오면 본 평가 전에 프롬프트를 고쳐야 한다. 추가 비용은 생성 5회+채점 15회로 무시 가능 | 5문항 1회 실행으로 점수·비용만 확인 |
| D-277 | 8/20 | 거부(R-) 15문항은 LLM Judge 호출 0회. 결과 파일의 judge_tokens 가 0 이 아니면 평가 실패로 처리 | 차단 정확도·과잉 차단률·대안 제시율은 전부 규칙 기반이다(기준 문서 §6·§10.5). Judge 를 태우면 비용만 쓰고 재현성도 떨어진다. judge_tokens=0 을 자동 검사하면 배선 오류가 조용히 지나가지 않는다 | R- 도 다른 영역과 동일하게 Judge 채점 |
| D-278 | 8/20 | 결과 파일 token_usage 는 by_model 을 원본으로 두고 generation_tokens·judge_tokens 를 파생시키며, unattributed_tokens(total−generation−judge)를 함께 기록. 조립은 models/shared/eval/token_usage.py 로 일원화 | llm.py 의 _total_tokens 는 역할이 아니라 모델명을 키로 집계한다(D-257). 두 모델명이 같으면 역할 분리가 원리적으로 불가능한데, 역할별 키만 있는 구조는 그때도 숫자를 만들어내 조용히 틀린 값이 남는다. unattributed 는 계획에 없던 모델 호출(법률 규제 2단 판정·self_check B안·디버그 잔재)을 드러내는 검증 장치다. 세 영역이 각자 dict 를 조립하면 필드명이 어긋나 compare_reports.py 가 오판한다(D-262) | 최상위 generation_tokens·judge_tokens·total_tokens 3필드 단독 구조 |
| D-279 | 8/20 | 평가 결과 파일 헤더에 §11.2 _CONDITIONS 5필드(generation_model·judge_model·dataset_version·fixture_version·trend_fixture_version)와 문항별 tokens 를 반드시 포함. 평가 시작 시 reset_total_tokens() 호출, generation_model==judge_model 이면 EvalPreflightError 로 중단 | 조건 필드가 없으면 compare_reports.py 의 before.get(key) 가 전부 None 이 되어 changed 가 항상 빈 리스트 → 모든 비교가 "프롬프트 튜닝 효과"로 오판된다. 기계가 막으려던 것을 기계가 통과시킨다(D-262·D-263). _total_tokens 는 프로세스 전역이라 초기화하지 않으면 이전 실행 잔재가 섞인다(D-267과 동일 원칙). 최상위 합계만 남기면 어느 문항이 비쌌는지·R- 에서 judge 가 0 인지 확인할 수 없다 | 헤더는 token_usage 만 기록 / 초기화는 호출부 재량 |
| D-280 | 8/20 | 이번 평가는 total_tokens 단위를 유지하고 금액 환산은 파일럿 전·후 !usage 2회 실측 대조로 대체. prompt/completion 분리 집계는 보류 | usage.total_tokens 는 input+output 합계인데 단가가 서로 달라 정확한 $ 환산이 불가능하다. 다만 지금 _total_tokens 를 다시 중첩 dict 로 바꾸는 것은 D-264~D-266 에서 이미 사고가 난 유형(int→dict 변경으로 테스트 4개 실패, 집계가 망가진 채 머지 직전까지 감)이고, 8/21 1차 측정 D-1 에 할 작업이 아니다. Judge 는 45문항×2회로 $30 중 극히 일부라 정밀 환산의 실익이 작다 | 즉시 prompt/completion 분리 집계 도입 |
| D-281 | 8/20 | compare_reports.py 구현 — 문서 §11.2 초안에 형식 검증(필수 헤더·judge_temperature)·area·item_count 게이트와 CLI·§11.1 표 생성을 추가. 반환 키 comparable·means·changed·reason 은 초안 그대로 유지 | 초안을 실행해 보니 ① 헤더 5필드가 양쪽 다 없으면 before.get()==after.get()==None 이라 changed 가 빈 리스트가 되어 "프롬프트 튜닝 효과"로 통과 ② area 미검사로 basic·consult 교차 비교 통과 ③ item_count 미검사로 문항 누락본 통과 ④ judge_temperature 미검사로 D-275 위반 측정 통과 ⑤ __main__ 부재로 문서의 실행 명령이 무동작 — 다섯 케이스 전부 재현됐다. D-279 가 지적한 오판을 막으려고 만든 도구가 그 오판을 그대로 낸다 | 문서 초안 그대로 복사 / 3단계 육안 확인만(D-262) |
| D-282 | 8/20 | 1차 측정 직후 `--validate` 단독 실행을 절차에 포함. 8/21 18:00 측정 종료 즉시 결과 파일 헤더를 검사한다 | 8/22 비교 시점에 8/21 결과의 헤더 누락을 발견하면 baseline 을 재측정해야 하고 $30 예산이 다시 나간다. 검증은 LLM 모델 호출 0회라 비용이 없다 | 8/22 비교 시점에 한 번만 확인 |
| D-283 | 8/20 | golden_dataset.md §11.2 코드 블록을 실구현으로 교체하고 §10.1 상태표를 구현 완료로 갱신 | 문서에 실린 코드와 실제 구현이 다르면 담당자가 "내 환경 문제인가"로 시간을 버린다(§10.1 v1.3 정정 사유). D-263 이 정한 "문서에 실린 코드는 상태표에 등재" 원칙의 연장 | 코드만 커밋하고 문서는 유지 |
| D-284 | 8/20 | assemble_response 는 state.get("status","ok") 로 읽는다 — state["status"] 직접 인덱싱 금지. 두 챗봇 공통 규칙 | 검증 함수 계약서 §8 노드는 pass 일 때 status 를 세팅하지 않고 부분 업데이트만 반환한다(§8.0-1). 즉 정상 통과한 요청에는 status 키가 존재하지 않아 KeyError → 바깥 except 에 먹혀 전 요청이 error 로 나가고 D-020 에 따라 크레딧까지 롤백된다. TypedDict 는 런타임 검증이 없어 BasicState 에 선언해도 키 존재를 보장하지 않는다. 컨설턴트가 이미 .get 을 쓰고 있었다(P-036) | state["status"] 유지 / 모든 노드가 status="ok" 를 명시 세팅 |
| D-285 | 8/20 | assemble_response 의 blocked 분기도 action·reason 에 폴백을 둔다 — action 은 enum(block·reask·warn) 밖이면 "block", reason 이 비면 "unknown", 두 경우 모두 logger.error 를 남긴다 | D-215 는 message 만 막았다. BlockedResult.action 은 enum 이고 reason 은 필수라 None 이 나가면 D-073 과 동일 유형의 502 다. `(state.get("issues") or [{}])[-1]` 폴백을 쓴다는 것은 issues 가 빌 수 있음을 이미 상정했다는 뜻인데 세 필드 중 하나만 방어했다 | message 만 방어(D-215 현행) |
| D-286 | 8/20 | copy_generation_failed → provider_error 매핑을 D-073 원안대로 유지. 의미 재검토는 P-055 으로 분리 | PR #147 은 unknown 으로 바꿨다. 의미상 unknown 이 더 정확하다는 주장은 성립하나, 서비스 개발 담당자가 D-073 기준으로 재시도·HTTP 매핑을 이미 구성했을 수 있고 코드에서 조용히 뒤집으면 D-046(계약 변경 시 공지 의무) 위반이다. D7 통합 D-1 에 합의 왕복을 추가하지 않는다 | PR 대로 unknown 으로 변경 / 즉시 서비스 개발 담당자와 재합의 |
| D-287 | 8/20 | run() 은 요청 구성과 그래프 실행을 별도 try 로 분리하고, 필수 키(chatbot_type·user_id·question·platform·store) 누락은 LLM 모델 호출 0회로 즉시 error 반환 | 하나의 except 로 묶으면 로그만 보고 "요청이 잘못된 건지 모델이 죽은 건지" 구분할 수 없다. 필수 키 누락은 어차피 channel_format 에서 터지는데, 앞에서 막으면 traceback 이 짧고 원인이 명확하며 비용이 0원이다 — check_input 을 LLM 모델 앞에 두는 것과 같은 원칙 | 단일 try 유지 |
| D-288 | 8/20 | build_basic_graph() 결과를 모듈 싱글턴으로 캐시하고 테스트용 reset_graph() 를 함께 제공. 컨설턴트도 동일 적용 | 현재는 요청마다 StateGraph 를 다시 컴파일한다. llm.py 의 _get_client() 가 클라이언트를 1회만 만드는 것과 같은 이유이고, D-206 으로 서비스가 asyncio.to_thread 를 쓰므로 동시 요청이 여러 스레드에서 들어와 재컴파일 비용이 그대로 p50 응답시간(§6 지표)에 실린다. reset 함수는 reset_client()·reset_total_tokens() 와 같은 테스트 격리 목적 | 요청마다 재컴파일 |
| D-289 | 8/20 | run() 계약 테스트를 PR #147 머지 조건에 포함 — 정상 경로 ok 반환·sources 타입·blocked enum·error reason enum·예외 미전파·내부 키 미누출 6항목 | D-210 이 "각 챗봇에 필수 배치"로 정한 항목이고, D-217 은 "프로덕션 수정 후 초록불 확인"을 요구한다. 실제로 이 테스트를 PR 원본에 돌리면 8건이 빨간불이고 수정본은 20건 전부 초록불이다 — 노드 단위 테스트가 전부 통과해도 서비스에 붙으면 502 가 나는 구조를 D7 통합 당일이 아니라 지금 드러낸다 | 통합 테스트 브랜치에서 수동 확인(D-210 이전 방식) |
| D-290 | 8/20 | P-048(토큰 집계 threading.Lock) 을 D7 통합 전에 적용 — 판단 시점 도래 | P-048 은 "D7 실연동 시 함께 판단(D-269)" 이었고 PR #147 로 그 시점이 왔다. D-206 의 asyncio.to_thread 로 동시 요청이 여러 스레드에서 call_llm 을 타므로 _total_tokens 의 get→set 사이에서 유실이 발생한다. 예산 참고 수치라 심각도는 낮지만 D-280 에서 금액 환산을 토큰 집계에 의존하기로 했고, D-269 가 이미 "3줄로 제거 가능"이라고 적어 두었다 | D8 이후로 재연기 |
| D-291 | 8/20 | run() 의 initial_state 에 deadline(D-144)과 source_gen_id 를 포함. 두 챗봇 공통 | D-144 는 "그래프 진입 시 state["deadline"] 설정"이라고 정했는데 진입점이 없어 미이행 상태였다 — PR #147 이 그 진입점이다. deadline 없이는 재생성 2회 + self_check 1회 + 429 백오프 14초가 서비스 60초를 잠식해 504 가 난다. source_gen_id 는 컨설팅→광고 파생 추적 경로(v10)라 진입점에서 빠지면 연계가 끊긴다 | 후속 PR 로 분리 |
| D-292 | 8/20 | 계약 테스트는 프로덕션 모듈에 테스트 전용 훅을 요구하지 않는다 — 가짜 그래프는 monkeypatch 로 main 이 import 한 이름(main.build_basic_graph)만 갈아끼운다 | 앞서 공유한 test_main_contract.py 는 build_basic.py 에 set_scenario() 가 있어야 돌았고, 그 함수는 전민재 PM 이 리뷰용으로 만든 임시 스텁이라 저장소에 없다. 서비스 개발 담당자가 test_main_contract.py 소스파일 실행 시 20 errors + 16 failed 가 났는데 근본 원인은 1건이다(autouse 픽스처 teardown 이 전 테스트를 무너뜨림). 프로덕션에 테스트 훅을 심으면 브랜치마다 존재 여부가 갈리고, 계약 테스트가 그래프 내부 구조에 결합돼 리팩토링 때 함께 깨진다 | 저장소 build_basic.py 에 set_scenario() 추가 |
| D-293 | 8/20 | 계약 검증의 무게중심을 assemble_response() 직접 호출로 둔다 — state dict 를 손으로 만들어 넣고 그래프·LangGraph·OpenAI 키 없이 검증한다. run() 테스트는 예외 미전파·필수 키·싱글턴·deadline 4가지만 담당 | P0 4건(status 키 부재·sources None·blocked action/reason None·D-073 매핑)이 전부 assemble_response 안에 있다. 이를 run() 으로 우회시키면 그래프 의존이 생겨 어느 브랜치에서 도는지가 결과를 좌우한다. 두 층으로 나누면 계약 층은 CI 에서 항상 돌고 진입점 층만 가짜 그래프가 필요하다 | 전 항목을 run() 경유로 검증(기존 판) |
| D-294 | 8/20 | 디스코드·PR 코멘트로 코드 파일을 공유할 때 ① 기준 브랜치·커밋 SHA 를 함께 적고 ② 그 브랜치에서 실제 실행한 결과를 붙이며 ③ 리뷰용 임시 스텁이 포함됐으면 명시한다 | 서비스 개발 담당자가 "제공 파일이 쓰는 브랜치와 통합 브랜치가 다른 것 같다"며 브랜치를 찾는 데 시간을 썼는데, 실제로는 브랜치 문제가 아니라 저장소에 없는 스텁 의존이었다. 원인 오진이 발생한 이유는 공유 시점에 기준과 실행 근거가 없었기 때문이다. D-211(요청 시 "확인"과 "신설"을 구분해 표기)과 같은 취지 | 파일만 첨부 |
| D-295 | 8/20 | 서비스 개발 담당자는 모델 측 단위·계약 테스트를 실행할 의무가 없다. D7 경계 검증은 tests/integration/test_d7_model_boundary.py 하나로 하고 관리는 서비스 개발 담당자가 한다. | 서비스 개발 담당자가 D7 통합 대신 모델 측 픽스처를 디버깅하게 됐다. 모델 내부(그래프·노드·state 키)를 모르는 담당자가 그 테스트를 고칠 수는 없으므로 시간이 그대로 소모된다. 경계 테스트는 run() 반환값이 ModelResult 계약을 지키는지만 보면 되고, 모델 내부 구조를 몰라도 돌아야 한다 | 서비스 개발 담당자가 모델 측 pytest 전체 실행 |
| D-296 | 8/20 | 통합 스모크에서 실제 LLM 모델을 태우는 항목은 RUN_LIVE_SMOKE=1 환경변수로만 실행한다. 기본 실행은 잘못된 요청 3종으로 LLM 모델 호출 0회 검증만 수행 | 통합 테스트가 매 실행마다 실제 카피·이미지를 생성하면 $30 한도가 CI 로 새어나간다. 반대로 실호출 경로를 아예 안 만들면 D7 당일에 처음 돌리게 된다. 기본은 무료·명시적으로 켤 때만 유료로 나눈다 — 골든 데이터셋 §10.5 의 "규칙 기반 지표는 먼저 돌려도 무료"와 같은 구분 | 항상 실호출 / 실호출 경로 미구현 |
| D-297 | 8/20 | 전민재 PM이 리뷰 코멘트로 첨부하는 참고 구현도 대상 브랜치에서 실행한 뒤 공유한다. 실행하지 않은 코드는 "미검증"이라고 명시한다 | 이번 건은 전민재 PM이 만든 재현 환경에서만 초록불이었고 저장소에서는 돌지 않았다. 리뷰어가 "20개 초록불"이라고 말하면 받는 쪽은 그대로 믿고 머지 준비를 한다. 검증 범위를 함께 밝히지 않으면 리뷰 코멘트 자체가 신뢰를 잃는다(D-217 이 테스트 결과를 근거로 삼는 전제) | 참고 구현은 검증 없이 공유 |

## 변경 이력
> 뒤집힌 결정은 **원래 줄을 지우지 말고** 아래 추가.

| 날짜 | 대상 | 변경 내용 | 사유 |
|------|------|-----------|------|
| — | — | — | — |
| 8/11 | D-016 | email → username | ORM 구현 상태와 맞춤 |
| 8/11 | D-009 | request_id → Idempotency-Key | 서비스 담당 구현 편의 존중 |
| 8/11 | D-0xx | Consultant 응답: proposals 평탄화 → strategy/reasons 유지 | actions를 copy로 합치면 프론트가 전략 카드 개별 렌더링 불가, reasons 의미 유실 | 평탄화 |
| 8/13 | 골든 데이터셋 | 컨설턴트 30문항 → 20문항 | golden_dataset.md v1.0 기준으로 3개 SDP 문항 수 통일 |
| 8/13 | 밀도 등급 | 사용자 노출 → 프롬프트 내부 힌트로만 사용 | 경계값이 임의 근사치라 외부 검증 불가 |
| 8/13 | get_market 시그니처 | (lat,lng,radius) → (lat,lng,radius,industry=None) | 캐시는 업종 무관 원본만 저장, 집계는 호출 시 계산 — 캐시 재사용률 개선(SDP §2.7 원안 대비 담당자 개선안 채택) |
| 8/13 | Contract v0.3 §4.5·§10.4·S-18 | Basic 10/Consultant 50 → Basic 50/Consultant 10 | D-006·D-021과 반전 기재됐던 것을 정정 |
| 8/13 | .env.example | DATABASE_URL 공란(로컬 폴백) → sqlite:///./data/app.db | 서비스·캐시 DB 통합. 단 캐시 테이블 생성 주체는 D-058로 별도 지정 |
| 8/13 | ERD | source_gen_id "FK 없이 값만 저장" → 실제 self-FK | 구현이 더 안전하므로 문서를 코드에 맞춤 |
| 8/13 | D-027 | platform 3종(blog 포함) → 2종(instagram·banner) | Contract v0.3·서비스 Literal·모델 코드 모두 2종으로 수렴 |
| 8/13 | D-019 | 이미지 재생성 1회 원칙을 코드에 반영(MAX_RETRY 공유 해제) | 공유 카운터로 인해 실질 2회 실행되던 것을 정정 |
| 8/14 | D4 ModelResult 구현 계약 | 최상위 결과 4종의 공통 `InboundModel`·ignored-field 이름 로깅·중첩 strict 테스트를 D4 완료조건에 추가 | PR #88 리뷰 후속 중 #89 명시 분기 이후에도 남은 관측성·테스트 경계를 한 브랜치에서 닫기 위함 |
| 8/13 | directory_structure.md §7.2 | shared/ 에 config.py 추가, retry.py 삭제, 상태 마커 도입 | §7.3 판정표와 트리 그림의 불일치 해소 |

## 보류 (Owner·Due 지정)

| ID | 항목 | 현재 기본안 | Owner | Due |
|----|------|-------------|-------|-----|
| P-001 | Proposal 3안 저장 방식 | 3개 내보내고 1개 라도 오류 발생 시 메시지 출력 및 로그 기록(재생성 루프 로직 구현 여부 논의 필요) | 전민재 PM | 미정 |
| P-002 | 법률 규제검증 RAG 전환 | 1주차 키워드 → 2주차 RAG, 실구현 8/19 그대로 유지 → 필요 시 8/18로 상향 (D-142) | 전민재 PM | 8/19 |
| P-003 | 데이터 보관기간·삭제 방식 | 미정 | 전민재 PM | 8/20 |
| P-004 | 재생성 시 동의창 재노출 | 재노출함 | 전민재 PM | 8/19 |
| P-005 | `self_check` 사실성 검증(B) | SHOULD, 예산 여유 시 | 전민재 PM | 8/21 |
| P-006 | 캐시 TTL 최종 확정 | → **종료(D-053)** | — | 8/12 종료 |
| P-007 | 상권 API 업종코드 체계 확인 | → **종료(D-086)** 신 2302 분류, 카페=I21201 | 컨설턴트 담당 | 8/14 종료 |
| P-008 | 밀도 등급 경계값 + 트렌드 방향 임계값(10%) 재조정 | 두 임계값 함께 처리, D9 [SHOULD] | 컨설턴트 담당 | 8/20 |
| P-009 | LLM 모델 최종 확정(gpt-4o-mini vs GPT-5.4 Mini/Nano) | 3문항 A/B 후 결정 | 전민재 PM | 8/14 |
| P-010 | Basic 응답의 suggested_chips 허용 여부 | 현행 빈 배열 고정(max_length=0) | 기본 챗봇 담당 | 8/14 |
| P-011 | market_cache UNIQUE(lat,lng,radius) 추가 시점 | D7 통합 시 서비스 담당이 DDL 추가(그전까지 upsert로 방어, D-050) | 서비스 담당 | 8/18 |
| P-012 | payments package·status enum 확정 | 임시안 유지, 결제 API 구현 전 확정 | 서비스 담당 | 8/19 |
| P-013 | 이미지 생성 장수·병렬화(3장 직렬 / 상위 1안만 / 3장 병렬) | D6에 1장 실측 후 결정 | 기본 챗봇 담당 | 8/18 |
| P-014 | 벤치마크 RAG 착수 시점 — 미착수 시 Hit Rate@5·MRR 산출 불가 | SDP상 D8, 지연 시 검색 지표를 보고서에서 제외할지 결정 | 전민재 PM | 8/18 |
| P-015 | CLIP 한국어 대응(다국어 CLIP 교체 vs 영문 이미지 프롬프트로 채점) | 영문 프롬프트 안이 비용상 유리 | 기본 챗봇 담당 | 8/19 |
| P-016 | shared 임베딩 래퍼(embed_texts) 제공 시점 | 벤치마크 인덱싱 착수(P-014) 전까지 제공 | 전민재 PM | 8/18 |
| P-017 | models/consult/config.py 재노출 제거 + 각 노드가 shared 직접 import | D7 통합 정리 시 | 컨설턴트 담당 | 8/18 |
| P-018 | 중첩 구조(BasicProposal·ProposalError·ConsultantStrategy·ConsultantAction) extra 정책 | ignore 통일 + 로깅 권고. 현행 strict는 channel_format 화이트리스트에 의존 — clip_score 노출 시 502 | 서비스 담당 | 8/15 |
| P-019 | GenerationResponse.result의 ModelResult union 잔존 처리 | 현행 유지 + 챗봇별 직렬화 확인 테스트 1개 추가 | 서비스 담당 | 8/15 |
| P-020 | 어댑터 배선 시 chatbot_type 단일 소스 확인(요청값 사용) | D4 /generate 구현 PR에서 확인 | 서비스 담당 | 8/15 |
| P-021 | 가게 주소·위치 수정 수단(PATCH /users/me vs 사이드바 입력) | D5 사이드바에 표시만, 수정 API는 D8 | 서비스 담당 | 8/18 |
| P-022 | production 필수 env 검증 범위 — validate_deploy_config가 SESSION_SECRET_KEY·SESSION_COOKIE_SECURE를 검사하는지 확인 | .env.example 그대로 배포 시 기동 실패(크래시 루프) | 서비스 담당 | 8/15 |
| P-023 | status=generating 잔여 행 처리(프로세스 중단 시 크레딧만 차감된 행) | 자동 복구는 미구현, 시연 전 수동 확인 절차로 대체 | 서비스 담당 | 8/21 |
| P-024 | datetime 저장 경로 통일(register_user aware 직접 저장 → _bind_utc 경유) | SQLite에선 결과 동일, 규칙만 통일 | 서비스 담당 | 8/18 |
| P-025 | market_cache upsert 적용(D-053 미이행) — 현재 INSERT만이라 동일 좌표 행 누적 | 읽기는 최신 행 기준이라 동작은 정상 | 컨설턴트 담당 | 8/18 |
| P-026 | `alternative`·`law` 를 서비스 응답 별도 필드로 노출 여부 논의 | 기본안: **message 문장에 포함**(§5.2). 별도 필드는 v0.3 계약 변경 필요(D-046) | 전민재 PM | 8/18 |
| P-027 | market_fixture 값의 출처(업종코드 교정 전/후) | 교정 후 실측값 사용, 미교정 시 현재값으로 파일럿 후 재측정 | 컨설턴트 담당 | 8/18 |
| P-028 | 검색 평가셋 진행 여부 — 벤치마크 KB 문서 ID(bm_###) 부여 | 미부여 시 Hit Rate@5·MRR을 보고서에서 제외 | 기본 챗봇 담당 | 8/18 |
| P-029 | allowed_numbers 반올림 허용 범위(정확 일치 vs ±5%) | 정확 일치로 시작, 파일럿 결과 보고 완화 검토 | 컨설턴트 담당 | 8/19 |
| P-030 | industry_code_map 상위 20종 확장 | 미착수 — 시연 Q&A 업종 변경 시 텍스트 매칭 폴백 | 컨설턴트 담당 | 8/19 |
| P-031 | 신규 API 키 5종 노출 점검 (.env.example 완료, git 과거 커밋 확인 필요) | git log -p --all -- .env 로 실키 이력 확인 | 전민재 PM | 8/18 |
| P-032 | 날씨 API 연동(기상청 단기예보 등) — add_sw_req_spec.md 추가 요구사항 명세서 5)번 사항 날씨 기반 카피 | [SHOULD]. 별도 함수·짧은 TTL(D-194). 외부 API 4번째라 전민재 PM 승인 후 착수(D-184) | 기본 챗봇 담당 | 8/20 |
| P-033 | 기본 챗봇 로컬 mock 전반을 실제 get_market/get_trend 반환값과 대조 | weather 외 다른 필드에도 같은 불일치가 있는지 확인 | 기본 챗봇 담당 | 8/18 |
| P-034 | image_gen이 image_prompt를 ranked_copies에 저장할지 | 현재 미저장이라 CLIP이 항상 copy로 폴백. 기록 전용 정책이라 우선순위 낮음 | 기본 챗봇 담당 | 8/20 |
| P-035 | regulation_node 테스트의 구 필드명(retry_count) 정리 | copy_retry_count로 통일 — 현재 의도한 시나리오를 검증하지 않음 | 기본 챗봇 담당 | 8/18 |
| P-036 | ConsultState에 status·issues 필드 추가 (D-143 이행) | assemble_response는 state.get("status","ok")로 동작하나, 보안 노드 라우팅 붙이려면 필수 | 전민재 PM | 8/18 |
| P-037 | 기본 챗봇 assemble_response 계약 테스트 (D-210·D-212) | 테스트 작성 완료 → 프로덕션 3줄 수정(D-213~215) 후 초록불 확인 | 기본 챗봇 담당 | 8/18 |
| P-038 | self_check_node의 issues.action 값 검토 — 현재 "block" 사용 | BlockedResult.action enum(block·reask·warn)에는 reject가 없어 현재는 통과. 검증 함수 실구현 후 재확인 | 전민재 PM | 8/18 |
| P-039 | 각 프롬프트 모듈에 FEWSHOT_TERMS·FEWSHOT_NUMBERS 상수 노출 (D-219 선행조건) | 예시 수정 시 상수도 함께 갱신 | 각 프롬프트 담당 | 8/18 |
| P-040 | eval_data_quality.py 구현 — 업종 매핑 커버리지·정확 판정 비율 산출 (D-222) | LLM 호출 0회라 예산 무관, 먼저 돌려도 됨 | 컨설턴트 담당 | 8/19 |
| P-041 | docs/improvements.md 신설 및 사례 1(업종코드 필터) 기록 (D-224) | 부록 D 템플릿 사용 | 컨설턴트 담당 | 8/19 |
| P-042 | 기본 챗봇 trend_for_copy의 keyword 전환 확인 (D-201 미이행) | 질문 원문 사용 시 캐시 적중률 0% + 문장 검색으로 fetch_raw가 None 반환 → 쿼터만 소모 | 기본 챗봇 담당 | 8/18 |
| P-043 | C- 골든 데이터셋 문항 실제 작성 개수 확인(20 vs 45) 및 확장셋 분리 | 20을 본 평가용으로 선별, 나머지는 [SHOULD] 표시 | 컨설턴트 담당 | 8/18 |
| P-044 | trend_fixture.related 와 FEWSHOT_TERMS 겹침 확인 (D-218) | strategy.py 실제 few-shot 값 확인 후 related 선정 | 컨설턴트 담당 | 8/18 |
| P-045 | 트렌드 유무 ablation 측정(트렌드 포함/미포함 근거 충실도 비교) | [SHOULD] 예산 여유 시. D-224 개선 사례 템플릿에 적합 | 컨설턴트 담당 | 8/20 |
| P-046 | OPENAI_JUDGE_MODEL 상위 모델 전환 여부 | 파일럿 후 !usage 실측 기준으로 판단(D-252) | 전민재 PM | 8/20 종료 |
| P-047 | D-051 LLM 모델 A/B 실행 — Judge 고정 후 generation_model 만 교체 | 구조 분리(D-251) 완료가 선행 조건 | 전민재 PM | 8/19 |
| P-048 | 토큰 집계 스레드 안전성(threading.Lock) 적용 여부 | D7 실연동 작업 진행 시 함께 판단(D-269) | 전민재 PM | 8/19 |
| P-049 | 1단 트리거 예외 추가 여부 — '매일 아침' 등 정상 카피 오탐(정상 40건 중 1건) | 2단 LLM 모델 실측 후 판단. 1단 recall 우선 원칙(D-272)을 유지하며 예외는 코드가 아닌 legal_kb.md 에서만 추가 | 전민재 PM | 8/21 |
| P-050 | check_output CTA 문맥 예외로 개인 연락처가 통과하는 범위 허용치 | 텍스트만으로 사업자·개인 연락처 구분이 불가능. D5 프론트엔드에서 사용자 확인 UI 로 보완할지 함께 판단(D-273) | 전민재 PM | 8/21 |
| P-051 | token_usage 의 prompt_tokens/completion_tokens 분리 집계 | D10 재측정 또는 D7 실연동 시 함께 판단. 타입 변경 시 D-266 원칙대로 검증 테스트를 같은 PR 에 포함(D-280) | 전민재 PM | 8/22 |
| P-052 | judge_model 상위 모델(GPT-5.4 계열) 전환 여부 | 본 평가 종료 후에만 검토 — 평가 중 변경 시 기측정 점수 전량 폐기(D-258·§11.4). 전환 시 judge_model 만 바꿔 "채점자 성향 차이"로 단독 비교(§11.2.1) | 전민재 PM | 8/22 |
| P-053 | eval_generation.py·eval_strategy.py·eval_refusal.py 의 token_usage.py 공통 사용 여부 확인 | 세 영역이 각자 헤더를 조립하면 compare_reports.py 가 오판한다(D-278·D-279). 파일럿 결과 파일 헤더 5필드 육안 대조 | 각 담당 | 8/21 |
| P-054 | compare_reports.py 를 CI 에 편입할지 (reports/ 변경 시 --validate 자동 실행) | 발표 이후 리팩토링 시 판단. 현재는 수동 실행으로 충분(D-282) | 전민재 PM | 8/22 |
| P-055 | copy_generation_failed 의 계약 reason 재검토(provider_error vs unknown) | 모델 내부 실패를 provider_error 로 올리면 서비스가 불필요한 재시도를 할 수 있다. 서비스 개발 담당자와 재시도 정책 확인 후 판단(D-286) | 전민재 PM | 8/22 |
| P-056 | D-143(status·issues 를 CommonState 로 승격) 미이행 확인 | 현재 state_common.py 에 두 필드가 없고 test_state_common.py 가 필드 집합을 고정하고 있다. 두 챗봇 main.py 가 스키마에 없는 키를 읽는 상태 — P-036 과 함께 처리 | 전민재 PM | 8/21 |
| P-057 | 컨설턴트 main.py 에도 D-285·D-287·D-288·D-291 동일 적용 여부 확인 | 기본 챗봇만 고치면 두 챗봇 진입점이 다시 갈라진다(D-002 공통 필드 단일 관리 취지) | 컨설턴트 담당 | 8/21 |
| P-058 | models/consult/tests/test_main_contract.py 도 동일 구조(D-292·D-293)로 정비 | 컨설턴트 계약 테스트가 같은 방식으로 그래프에 결합돼 있는지 확인 후 판단. P-057 와 함께 처리 | 컨설턴트 담당 | 8/21 |
| P-059 | tests/integration/ 을 CI 기본 실행 대상에 포함할지 | RUN_LIVE_SMOKE 미설정 시 LLM 모델 호출 0회라 비용은 없으나, models/consult/main.py 미구현 브랜치에서 빨간불이 난다. 두 챗봇 run() 머지 후 판단(D-296) | 서비스 담당 | 8/21 |
