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
| D-017 | 8/11 | `banned_keywords`: JSON 먼저 → DB 나중 | 서비스 개발 담당 DDL 대기 없이 D2 착수 가능 | 처음부터 DB |
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
| D-053 | 8/13 | market_cache 중복 방지 = upsert 선적용, UNIQUE 인덱스는 D7에 서비스 개발 담당이 추가 | 서비스 개발 담당 DDL 대기 없이 방어 가능(D-017과 동일 패턴) | DDL 완료까지 대기 |
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
| D-183 | 8/18 | 회원가입 business_type 드롭다운 제한 검토 (서비스 개발 담당, D8) | 매핑에 없는 업종을 입력받아 부정확한 수치를 주는 것보다 입력을 제한하는 편이 안전. Contract §4.2 자유 문자열 변경 필요(D-046 절차) | 자유 문자열 유지 |
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
| D-298 | 8/21 | Judge 안정성 통과 기준을 D-276 의 "동일 응답 3회 채점 시 편차 0" 에서 3계층으로 교체 — ① 셀(문항×rubric) max-min ≤ 1 ② 문항 rubric 평균 max-min ≤ 0.5 ③ 데이터셋 llm_judge_avg 재현 SD ≤ 0.05. ③이 실질 기준 | temperature=0 은 "가장 확률 높은 토큰 선택"이지 결정론이 아니다. 배치 구성에 따라 GPU 축약 순서가 바뀌면 로짓 하위 자릿수가 달라지고 두 등급 점수가 비슷할 때 argmax 가 뒤집힌다 — API 기반 Judge 가 원리적으로 만족할 수 없는 기준이었다. 기준을 못 맞춰 본 평가를 못 돌리면 기준이 평가를 막은 셈이 된다. D-276 의 목적("자가 흔들리면 +0.5 개선을 증명할 수 없다")은 절대 결정론이 아니라 "노이즈가 재려는 효과보다 충분히 작은가"로 달성한다 | D-276 편차 0 유지 후 Judge 프롬프트 보완 / 상위 Judge 모델로 교체 |
| D-299 | 8/21 | 최소 검출 가능 효과(MDE)를 ±0.07 로 명시하고 결과 파일·비교표에 함께 기록. 이보다 작은 변화는 발표에서 "개선"이라 부르지 않는다 | 관측된 셀 흔들림 25% 를 60문항×rubric 4 = 240셀로 외삽하면 llm_judge_avg 재현 SD 0.015, 95% 재현 폭 ±0.03, 두 측정 차이의 3σ 0.06 이다. 튜닝 효과 +0.3~0.5 는 노이즈의 5~8배라 측정에 지장이 없다. 반대로 MDE 를 명시하지 않으면 +0.04 같은 노이즈 수준 변화를 개선으로 발표하게 된다 | MDE 미명시 / 소수점 변화도 개선으로 보고 |
| D-300 | 8/21 | 생성 실패 문항(C-003 actions_wrong_length)은 Judge 안정성 파일럿의 실패로 보지 않는다. 안정성 표본에서만 제외하고 failure_rate·contract_compliance 에는 그대로 계산하여 올린다 | 안정성 파일럿은 "생성 1회로 고정한 응답을 3회 채점"(D-276)이라 설계상 생성 품질과 독립이다. 생성이 실패하면 채점 대상이 존재하지 않을 뿐 자[尺]가 흔들린 것이 아니다. 두 트랙을 묶으면 생성 버그 하나가 Judge 검증 전체를 막는다 | C-003 수정 완료 후 안정성 파일럿 재실행 |
| D-301 | 8/21 | actions_wrong_length 를 ① 코드 버그(파서·검증 로직) ② 모델 출력 품질(LLM 이 actions 개수를 못 맞춤) 로 분류한다. ①은 본 평가 전에 수정, ②는 **수정하지 않고 baseline 에 남긴다** | baseline 을 예쁘게 만들려고 프롬프트를 미리 고치면 개선 폭을 스스로 지운다. 5문항 중 1건이면 contract_compliance 80% 가 baseline 이고 튜닝 후 100% 가 되면 "+20%p" 라는 근거가 생기는데, 지금 고치면 처음부터 100% 라 발표에서 보여줄 것이 없다. §11.2 "한 번에 하나만 바꾼다"·D-261 "바꾼 것 한 줄"과 같은 취지다. 또한 self_check reject → 재생성 1회(D-156)가 돌았는지, 실패가 failure_rate(status≠ok)와 contract_compliance 중 어디로 귀속되는지 먼저 확정한다 | 원인 구분 없이 즉시 수정 후 재측정 |
| D-302 | 8/21 | 앵커 문항 3건 도입 — 튜닝 전 측정에서 저장한 응답을 튜닝 후 측정 때 그대로 재채점해 Judge drift 를 검출한다. 평균 이동 허용 오차 ±0.25, 초과 시 비교표에 이동값을 함께 기록 | 셀 단위 노이즈는 문항 수로 상쇄되지만(D-299), Judge 가 시간에 따라 통째로 이동하면 평균으로도 상쇄되지 않는다(제공자 백엔드 업데이트 등). 응답이 동일한데 점수가 달라졌다면 모델이 개선된 게 아니라 자[尺]가 움직인 것이다. 비용은 3건 재채점이라 무시할 수준이고, 이 장치가 없으면 "+0.3 개선"이 Judge 이동인지 모델 개선인지 구분할 방법이 없다 | drift 검출 장치 없이 전후 비교 |
| D-303 | 8/21 | Judge 호출에 seed 를 고정하고 응답의 system_fingerprint 를 결과 파일에 기록한다 | seed 는 결정론을 보장하지 않지만 재현 확률을 높이고, system_fingerprint 가 달라지면 제공자 백엔드가 바뀐 것이라 D-302 앵커 drift 의 원인을 즉시 특정할 수 있다. 기록이 없으면 "왜 점수가 움직였나"에 답할 방법이 없다 | seed·fingerprint 미기록 |
| D-304 | 8/21 | 이미 측정된 파일럿 데이터를 새 기준으로 재판정하고, 통과 시 재실행 없이 5문항 → 전체 평가로 진행한다 | 보고된 실측치를 D-298 기준에 넣으면 편차 2 이상 셀 0건·문항 평균 편차 0건·60문항 환산 SD 0.0161(기준 0.05)로 통과한다. 기준 변경 때문에 이미 확보한 데이터를 버리고 다시 돌리면 시간과 예산을 이중으로 쓴다. 담당자 컨디션 이슈가 보고된 상황이라 재실행을 요구할 근거가 더 약하다 | 새 기준으로 파일럿 재실행 |
| D-305 | 8/21 | PR #103(D4 생성 오케스트레이션) 승인·즉시 머지. 남은 지적 3건은 D7 후속 이슈로 분리 | 8/14 등록·8/18 재문의 후 7일간 리뷰 대기했고 그 사이 후순위 PR(#147)이 먼저 처리됐다 — 우선순위 판단 오류이며 전민재 PM 병목이다. 요청된 리뷰 포인트 4건(트랜잭션 경계·중복 호출/과금 방지·settle/rollback·source 관리권)은 모두 통과했고, 모델 호출 중 DB 트랜잭션 미보유를 테스트로 고정한 점·보상 commit 실패 시 마커 reset 후 durable charge 유지 처리는 계약 요구를 넘어선다. 남은 지적은 전부 D7 경계 문제라 이 PR 범위가 아니다 | 3건 반영 후 재리뷰 |
| D-306 | 8/21 | 컨설팅→광고 연계 데이터의 단일 소스는 ModelRequest.source_context 로 확정. models/basic/main.py 와 CommonState 의 source_gen_id 를 source_context 로 교체한다. 수정 담당은 전민재 PM | 서비스는 공개 요청의 source_gen_id 를 서버가 관리권·타입·상태로 검증한 뒤 전략 원문(strategy·reasons·sources)으로 치환해 보낸다 — 프론트가 남의 generation_id 를 주입할 수 없으므로 이쪽이 옳다. 반면 모델 main.py 는 request.get("source_gen_id") 를 읽어 항상 None 이 되고 전략 데이터가 통째로 버려진다. 실행 확인 결과 서비스가 보내는 source_context 를 모델이 한 번도 읽지 않는다. D-291 에서 해당 줄을 넣을 때 ModelRequest 를 대조하지 않은 것이 원인이다 | 서비스가 source_gen_id 를 함께 보내도록 ModelRequest 확장 |
| D-307 | 8/21 | 모델 타임아웃은 이중 방어로 정의한다 — 서비스의 asyncio.wait_for(60초)는 **응답만 끊는 마지막 방어선**이고, 실제로 작업을 중단시키는 것은 모델 내부 deadline(LLM_DEADLINE_SECONDS=50)이다. 이 관계를 CI/CD 문서와 validation_contract §12.4 에 명시 | D-206 의 asyncio.to_thread 는 스레드를 취소할 수 없다. 실험 결과 서비스가 2초에 TimeoutError 를 내고 크레딧을 롤백한 뒤에도 모델 스레드는 8초를 끝까지 채우며 OpenAI 토큰을 계속 소모했다. 즉 서비스 타임아웃만으로는 $30 예산이 보호되지 않는다. 50 < 60 관계가 우연이 아니라 필수 조건임을 문서에 남기지 않으면 누군가 값을 뒤집는다(D-054 재발 유형) | 서비스 타임아웃만으로 충분하다고 보고 모델 deadline 제거 |
| D-308 | 8/21 | 컨설턴트 strategy.actions 개수 계약은 **1~3개**이며 backend/schemas.py 의 ConsultantStrategy 가 단일 소스다. P-062 종료 | PR #103 스키마에 min_length=1, max_length=3 으로 이미 확정돼 있다. 김재헌님이 보고한 actions_wrong_length 의 정체가 이것이다. 컨설턴트 프롬프트·평가 스크립트가 다른 숫자를 쓰면 여기서 갈리므로, 두 곳을 이 값에 맞춘다. 계약을 코드 세 곳에 중복 정의하면 언제든 다시 어긋난다(D-054 원칙) | 모델 쪽 기준으로 서비스 스키마 완화 |
| D-309 | 8/21 | tests/integration/test_d7_contract_fitness.py 를 CI 기본 실행 대상에 포함. 모델이 낼 수 있는 응답 모양을 서비스 Pydantic 에 직접 넣어 검증하며 LLM 호출은 0회 | 두 PR 이 각자 내부적으로는 옳은데 맞물리는 지점에서 어긋난다. 통합 당일에 발견하면 그날 하루를 잃는다(D-217 과 같은 취지). 비용이 0 이므로 매 PR 마다 돌려도 부담이 없고, MODEL_READS 상수가 두 팀의 명시적 합의 지점 역할을 한다 — 모델 쪽이 읽는 키를 바꾸면 이 상수도 함께 바꾸게 되어 변경이 드러난다 | 통합 브랜치에서 수동 스모크로만 확인 |
| D-310 | 8/21 | 컨설턴트 assemble_response 는 sources·reasons 를 최소 1개, suggested_chips 를 정확히 3개로 보장한다. 기본 챗봇의 `state.get("sources") or []` 폴백(D-284)을 그대로 복사하지 않는다 | ConsultantModelResult 는 sources·reasons 에 min_length=1, suggested_chips 에 min_length=3·max_length=3 을 건다. Basic 은 sources 최소 개수가 없어 빈 배열이 안전하지만 컨설턴트는 즉시 ValidationError → model_result_validation_failed → 500 이 된다. P-057(두 챗봇 진입점 동일 적용)를 기계적으로 수행하면 오히려 깨지는 지점이다 | 두 챗봇에 동일 폴백 일괄 적용 |
| D-311 | 8/21 | required status check 를 강제할 수 없는 동안, 리뷰어는 승인 코멘트에 Python tests·Deployment assets·Compose smoke test 3개 Job 의 통과 링크를 남긴 뒤 머지한다 | CI/CD 문서가 "현재 저장소 플랜에서는 required status check 를 강제할 수 없다"고 명시한다. 즉 빨간불 PR 도 물리적으로 머지 가능하다. 링크를 남기면 확인 사실이 기록으로 남고, 나중에 "왜 깨진 코드가 main 에 들어갔나"를 추적할 수 있다. 저장소 설정으로 강제할 수 있는지는 별도 확인한다 | 리뷰어 재량 확인(현행) |
| D-312 | 8/21 | MODEL_REQUEST_TIMEOUT_SECONDS 를 60 → 180 으로 상향. 단 **임시값**으로 표시하고 콜드 스타트 제거 후 실측으로 재산정한다 | 로그 실측 결과 60초는 생성이 아니라 HuggingFace 가중치 다운로드에 쓰였다(요청 시작~가중치 준비 완료 140.3초). asyncio.wait_for 가 to_thread 스레드를 못 멈추므로(D-307) 타임아웃을 짧게 두면 토큰은 다 쓰고 결과만 버리는 최악의 조합이 된다 — 이 점에서 상향은 옳다. 다만 140초는 콜드 스타트 1회 비용이지 요청당 비용이 아니므로, 180 이라는 값 자체는 원인이 아니라 증상에 맞춘 값이다 | 60초 유지 / 300초 이상으로 대폭 상향 |
| D-313 | 8/21 | HF_TOKEN 을 VM `/srv/team6/app/.env` 에 추가하고 HF_HOME 을 호스트 바인드 마운트로 분리, 가중치는 앱 기동 시 사전 로딩한다 | 로그의 "unauthenticated requests to the HF Hub" 경고가 이번 타임아웃의 실제 원인이다. 익명 요청은 rate limit 이 걸리고, 캐시가 컨테이너 안에 있으면 배포할 때마다 140초를 다시 낸다. 'Loading weights [00:00<00:00]' 은 텐서 로딩 자체가 1초 미만임을 보여주므로 병목은 전적으로 다운로드다. 이 조치로 콜드 스타트가 사라지면 180초 자체가 불필요해질 수 있다. HF_TOKEN 은 API 키이므로 GitHub Secrets 가 아니라 VM `.env` 에만 둔다(CI/CD 문서 원칙) | 타임아웃만 늘리고 콜드 스타트 방치 |
| D-314 | 8/21 | 이미지 생성 경로에 자체 타임아웃을 신설한다. 서비스 타임아웃 = LLM 예산 + 이미지 예산 + 여유 로 정의 | D-307 은 "실제 중단은 모델 deadline(50초)" 이라고 정리했으나, LLM_DEADLINE_SECONDS 는 call_llm 에만 전달되어 이미지 생성·가중치 로딩은 보호 범위 밖이다. 이번 60초 중 단 1초도 deadline 의 보호를 받지 못했다. 이미지 예산이 정의되지 않으면 서비스 타임아웃 값의 근거를 댈 수 없다 | LLM deadline 만으로 충분하다고 보고 유지 |
| D-315 | 8/20 | stale 복구 임계를 model_timeout_seconds 의 배수에서 분리해 별도 상수(기본 120초)로 둔다 | recover_stale_generating 이 `2 * model_timeout_seconds` 를 쓰므로 타임아웃 상향이 크레딧 회수 지연으로 전이된다(120초 → 360초). 사용자가 [다시 시도]를 눌러도 6분간 pending 만 돌려받게 되며, 이는 SDP §6.5 가 "컴플레인 1순위"로 지목한 상황이다. 타임아웃을 올린 것과 크레딧을 언제 돌려줄지는 별개 판단이다 | 배수 유지(2배) |
| D-316 | 8/21 | 생성 결과 계약 위반을 **결정론적 실패**(JSON 파싱 불가·필수 필드 누락·타입 불일치)와 **확률적 실패**(스키마는 맞고 값만 범위 밖 — 배열 길이·enum 밖 값)로 분류한다. 전자는 D-139 원안대로 즉시 실패, 후자는 복구를 허용한다. 판별 기준은 "재시도 1회로 통과율이 유의하게 오르는가"의 실측 | actions_wrong_length 는 같은 프롬프트·같은 입력으로 재시도했을 때 5/5 가 통과했다. 결정론적 형식 오류였다면 재시도해도 똑같이 깨진다 — 즉 D-139 가 상정한 "재시도해도 소용없는 형식 오류"가 아니라 temperature 0.3 의 확률적 변동이다. 개별 항목마다 예외를 허락하면 유사 사례가 올 때마다 전민재 PM 판단이 필요하지만, 분류 기준을 두면 담당자가 실측으로 스스로 판정할 수 있다 | actions_wrong_length 만 D-139 예외로 허락 |
| D-317 | 8/21 | actions 개수 복구는 **절단 우선, 재생성은 0개일 때만**. 재생성 상한 1회, 카운터는 strategy_retry_count 로 분리, deadline 잔여 예산이 없으면 재생성을 포기한다 | actions 4~5개는 "답을 못 낸 것"이 아니라 "많이 낸 것"이라 앞 3개로 자르면 LLM 모델 호출 0회로 해결된다(실측: 5건 전부 초과면 추가 호출 0회, 전부 0개면 5회). 0개만 만들어낼 수 없어 재생성이 불가피하다. 또한 strategy 재시도 1회 × self_check 재생성 1회(V-03)가 곱해져 생성 호출이 최대 4회가 되므로, 생성 1회 10초 가정 시 40초로 LLM_DEADLINE_SECONDS(50)를 거의 소진한다 — 재시도는 반드시 예산 안에서만 수행한다(D-291·D-307) | 조건 없이 재시도 1회 허용 |
| D-318 | 8/21 | 이미 실행한 60문항 결과를 **baseline 으로 확정**하고, 복구 로직(D-317)은 "튜닝 후" 측정에만 적용한다. D-301 유지 | D-301 은 "모델 출력 품질 문제는 고치지 말고 baseline 에 남긴다"로 정했다. 지금 복구를 넣으면 contract_compliance 가 baseline 부터 100% 가 되어 개선 폭을 스스로 지운다. 담당자가 이미 "복구 없음 55/60" 과 "복구 있음 60/60" 을 모두 측정했으므로 LLM 모델 A/B 데이터가 확보돼 있다 — 91.7% → 100% (+8.3%p) 가 그대로 발표 자료가 된다. ⚠️ 그 60문항 실행이 §10.4 결과 파일 형식으로 저장돼 있어야 baseline 으로 쓸 수 있다 | 복구를 baseline 부터 적용 |
| D-319 | 8/21 | 결과 파일 metrics 에 actions_truncate_rate·actions_retry_rate 를 기록하고 compare_reports.py 의 _LOWER_IS_BETTER·_PERCENT_METRICS 에 등록한다 | 복구를 넣으면 contract_compliance 는 100% 가 되지만, 그것이 "프롬프트가 계약을 제대로 전달하게 된 것"인지 "복구가 가려준 것"인지 구분할 수 없다. 복구 발생률을 함께 남기면 이후 프롬프트 개선의 효과를 별도로 측정할 수 있다. 지표를 신설하면 compare_reports 에 등록해야 비교표에서 방향(굵게)과 단위(%p)가 붙는다(D-283 후속) | contract_compliance 만 기록 |
| D-320 | 8/21 | 프롬프트 문구 강화는 되돌리고, 이번 변경은 복구 로직 단독으로 적용한다 | 문구 강화의 효과는 1/5(20%)에 그쳤다. 복구 로직과 함께 넣으면 "어느 쪽이 +8.3%p 를 만들었는가"를 분리할 수 없다(§11.2.2 "한 번에 하나만 바꾼다"). 효과가 미미한 변경을 섞어 원인 분리를 포기할 이유가 없다. 프롬프트 개선은 D-319 의 복구 발생률을 지표로 삼아 별도 실험으로 진행한다 | 문구 강화 + 복구 로직 동시 적용 |
| D-321 | 8/21 | 계약 준수율 개선을 발표에 실을 때 McNemar 검정 결과(불일치 쌍 수와 p 값)를 함께 기록한다 | 60문항 중 불일치 5건이 전부 한 방향이므로 단측 p=0.031, 양측 p=0.063 이다. 유의하긴 하나 표본이 작아 "+8.3%p 개선" 만 제시하면 질의응답에서 근거를 대지 못한다. D-299 가 llm_judge_avg 에 MDE 를 명시하기로 한 것과 같은 취지 — 비율 지표에는 검정 결과가 그 역할을 한다 | 변화폭만 기록 |
| D-322 | 8/21 | 전민재 PM 관리 테스트는 다른 담당자 모듈의 **비공개 이름**(밑줄로 시작하는 상수·함수)에 의존하지 않는다. 진입점 검증은 공개 API(`run`·`reset_graph`·`build_basic_graph`)로만 한다 | `test_d7_contract_fitness.py` §5 가 `main._REQUIRED_KEYS` 를 읽고 있었는데, 기본 챗봇 담당이 그 상수를 인라인으로 옮기자 CI 가 `AttributeError` 로 깨졌다. 밑줄 이름은 관리자가 언제든 개명·인라인할 수 있는 내부 구현이므로, 남이 붙잡으면 리팩토링할 때마다 남의 CI 가 깨진다. `set_scenario` 사고(D-292)와 같은 유형이 형태만 바꿔 재발했다. 실측 확인: 재작성 후 `_build_initial_state` 를 통째로 개명해도 48건 전부 통과한다 | `models/basic/main.py` 에 `_REQUIRED_KEYS` 를 공개 상수로 승격 |
| D-323 | 8/21 | 선언 대조 검사(`MODEL_READS_REQUIRED` ↔ 상수 비교)를 **동작 검사**로 대체한다 — 필수 키를 하나씩 뺀 요청을 `run()` 에 넣어 `status="error"` 이고 그래프가 호출되지 않았는지 확인 | 같은 것을 "상수 이름"이 아니라 "동작"으로 검증하면 구현 변경에 영향받지 않는다. 덤으로 "필수 키가 없으면 LLM 모델 호출 0회로 즉시 error 반환한다."(D-287)까지 함께 고정된다 — 선언 대조로는 잡을 수 없던 항목이다. 가짜 그래프를 monkeypatch 로 주입하므로 LangGraph·OpenAI 없이 CI 에서 돈다 | 선언 대조 검사 삭제(§1 만 유지) |
| D-324 | 8/21 | 계약 필드 이름 변경은 **관리자가 달라도 한 PR 로 원자적으로** 넣는다. 이번 건은 `models/shared/state_common.py`(전민재 PM)와 `models/basic/main.py`(기본 챗봇 담당)를 같은 PR 에 포함한다 | 둘 중 하나만 머지하면 CI 가 각각 1건씩 빨간불이라 어느 쪽도 단독으로 머지할 수 없다(실측: 전민재 PM 측만 1 failed, 모델 측만 1 failed, 둘 다 48 passed). 더 위험한 것은 조용한 실패다 — `state_common.py` 만 바꿔도 `main.py` 가 옛 키를 읽으면 `None` 이 들어갈 뿐 아무것도 터지지 않는다(TypedDict 는 런타임 검증이 없다). §7.1 "한 파일에는 관리자 한 명" 은 유지하되, 원자성이 필요한 계약 변경은 예외로 두고 관리자를 리뷰어로 지정한다 | 관리자별로 PR 분리(어제 권고안) |
| D-325 | 8/21 | 남의 관리 파일을 포함한 PR 은 ① 커밋 메시지에 포함 사유를 남기고 ② PR 본문 "리뷰어 주의사항" 을 갱신하며 ③ 해당 디렉터리 관리자를 리뷰어로 지정한다 | 리뷰 요청 후 범위가 바뀌면 리뷰어가 "내가 봤던 그 PR" 이 아닌 것을 승인하게 된다. D-294(공유 시 기준·실행 근거 명시)의 PR 판이며, 관리 경계를 넘은 사실이 기록으로 남아야 나중에 "왜 이 파일이 여기서 바뀌었나" 를 추적할 수 있다 | 조용히 커밋만 추가 |
| D-326 | 8/21 | 열린 PR 에 커밋을 얹을 때는 `merge` 를 쓰고 `rebase` + force-push 를 하지 않는다 | 리뷰 요청이 이미 나간 상태에서 force-push 하면 리뷰어가 남긴 라인 코멘트가 outdated 로 밀리고 "이전 커밋과의 차이" 를 볼 수 없다. 이번 PR 은 리뷰 대기 중이므로 이력 보존이 우선이다 | rebase 로 이력 정리 후 force-push |
| D-327 | 8/21 | push 전에 CI 와 **동일한 3개 명령**(`uv sync --locked --all-groups` · `uv run --locked --all-groups pytest` · `uv run --locked --group dev ruff check .`)을 로컬에서 실행해 초록불을 확인한다 | D-297 이 정한 "실행한 뒤 공유" 원칙을 PR 커밋에도 적용한다. 이번 CI 실패 2건은 로컬에서 전체 pytest 를 한 번만 돌렸어도 push 전에 드러났다. required status check 를 강제할 수 없는 저장소 상태(D-311)에서는 로컬 확인이 사실상 유일한 사전 방어선이다 | 변경한 테스트 파일만 부분 실행 |
| D-328 | 8/21 | 미구현 기능 때문에 실패하는 테스트를 `xfail` 로 우회하지 않는다. 부득이하게 쓸 때는 `strict=True` 와 함께 해제 조건(PR 번호)을 reason 에 명시한다 | xfail 로 우회하면 PR 이 3단계(본체 → 구현 → 마크 해제)로 늘어나고, 마지막 단계를 잊으면 그 테스트는 영원히 실행되지 않는다. `strict=True` 는 구현이 끝나 통과하는 순간 "xfail 인데 통과했다" 로 빨간불을 내 마크 제거를 강제한다. 이번 건은 한 줄 수정이라 우회할 이유가 없다 | D-306 미반영 테스트를 xfail 처리 후 별도 PR 로 해제 |
| D-329 | 8/21 | LLM Judge 프롬프트에는 채점 대상 텍스트만 넣는다. image_b64 등 비텍스트 필드는 models/shared/eval/judge_payload.py 의 공용 함수로 제거하며, 파일럿과 본 평가 3개가 모두 이 함수를 쓴다 | 파일럿이 응답을 그대로 json.dumps() 해 프롬프트에 넣어 context length exceeded 로 실패했다. 실측: 1024 PNG 3안 = 약 175만 토큰(gpt-4o-mini 컨텍스트 128K의 13배). 골든 데이터셋 rubric 4항목은 전부 텍스트 카피에 대한 것이라 이미지는 애초에 채점 대상이 아니고, 이미지 품질은 eval_image.py 의 CLIP Score 소관이다(§7.2). 서비스는 같은 문제를 이미 풀었다 — serialize_model_result_for_storage 가 DB 저장 시 image_b64 를 빼고 테스트로 고정돼 있다. 파일럿에만 필터를 넣으면 본 평가에서 같은 버그가 재발하므로 공용으로 뺀다 | _judge_once() 안에서만 image_b64 제거 |
| D-330 | 8/21 | 페이로드 정제는 이중 방어로 한다 — ① 알려진 비텍스트 필드를 이름으로 제거 ② 남은 문자열·페이로드가 상한을 넘으면 **자르지 않고 예외**를 던진다 | 블랙리스트만 두면 나중에 다른 큰 필드(raw_response·data URI 등)가 생겼을 때 또 터진다. 자르는 방식을 먼저 만들었다가 폐기했는데, 잘린 응답을 채점하면 "무엇을 채점했는지" 가 달라져 골든 데이터셋 제1 요건인 재현성이 깨지기 때문이다(§1.4). 멈추고 원인을 찾는 편이 낫다. 실측 확인: DROP_FIELDS 밖의 30,000자 필드와 비정상적으로 긴 카피(5,000자) 모두 예외로 잡힌다 | 상한 초과분 자동 절단 |
| D-331 | 8/21 | 평가 결과 파일에도 이미지를 저장하지 않는다. §10.4 DoD ③ "문항별 원본 응답 보존" 은 이미지를 제외한 텍스트 기준으로 해석하고, 제거 내역을 dropped_fields 로 함께 남긴다 | 파일럿이 details 에 응답을 그대로 저장해 결과 JSON 이 수 MB 가 되고, Git 에 커밋되면 저장소가 부푼다. 조희원님이 지적한 프롬프트 결함과 원인·해법이 동일한 두 번째 결함이었다. 서비스가 DB 저장 시 image_b64 를 빼는 것과 같은 판단이며, 무엇을 뺐는지 남기면 나중에 "이미지가 왜 없나" 를 되묻지 않아도 된다 | 원본 그대로 보존 |
| D-332 | 8/21 | 문항당 judge 토큰 상한(6,000)을 두고 초과 시 경고를 출력한다 | 이번 사고는 컨텍스트를 초과해 실패했지만, 이미지가 작았다면 통과하며 조용히 예산을 태웠을 것이다(실측: 512 JPEG 3안 = 7만 토큰/문항, 본 평가 60문항×3회 = 1,260만 토큰). D-278 의 item_token_delta() 가 문항별 토큰을 이미 재고 있었는데 상한 검사가 없어 그냥 지나갔다. 카피 3안+rubric 이면 회당 1,000 토큰 안쪽이 정상이라 3회 기준 6,000 이면 충분한 여유다 | 토큰 기록만 하고 검사 없음 |
| D-333 | 8/21 | 실호출 경로는 반드시 소규모 파일럿을 먼저 돌린다. 본 평가는 파일럿 통과 후에만 실행한다 | 이번 결함이 본 평가 60문항에서 처음 드러났다면 실패든 통과든 예산 피해가 12배였다. D-276 이 파일럿을 5문항으로 설계한 이유가 "자[尺] 검증" 이었는데, 실제로는 **비용 사고의 조기 차단**이라는 효과가 더 컸다. D-296(RUN_LIVE_SMOKE 게이트)과 함께 "유료 경로는 항상 작게 먼저" 원칙으로 묶는다 | 파일럿 생략하고 본 평가 직행 |
| D-334 | 8/21 | 계약 필드 이름을 바꿀 때 `git grep -n "<옛_이름>" -- models/ docs/` 로 전수 확인하고, 각 히트를 눈으로 판정한 뒤 PR 을 올린다. backend/ 는 검사 범위에서 제외한다 | D-306(source_gen_id → source_context) 영향 파일 목록에서 models/basic/tests/test_main_contract.py 가 누락돼 CI 가 KeyError 로 실패했다. models/basic/main.py 는 정상 반영됐고 테스트만 옛 이름을 단언하고 있었다. 목록을 사람이 기억으로 만들면 빠진다 — 기계로 훑고 사람이 판정한다. backend/ 를 제외하는 이유는 GenerateRequest.source_gen_id 가 공개 요청의 정당한 필드로 계속 존재해야 하기 때문이다 | 영향 파일 목록을 기억에 의존해 작성(현행) |
| D-335 | 8/21 | 같은 계약을 두 테스트 파일이 중복 검증하지 않는다. 분담 기준은 **backend.schemas 를 import 하는가** — import 하면 '서비스↔모델 키 매핑'(tests/integration/test_d7_contract_fitness.py, 전민재 PM 관리), 하지 않으면 'run() 반환 계약'(models/*/tests/test_main_contract.py, 챗봇 담당 관리) | source_context 가 그래프에 도달하는지를 두 파일이 각자 검증하고 있었고, 계약이 바뀌자 한쪽만 고쳐져 CI 가 깨졌다. 중복이 있는 한 같은 사고가 반복된다. "서비스가 보낸 키가 모델에 도달하는가" 는 서비스 스키마를 봐야 판단할 수 있으므로 전자의 일이고, main_contract 에 있던 것은 중복이었다. 이 기준은 D-295(서비스 개발 담당은 모델 내부를 몰라도 돌릴 수 있어야 한다)의 반대 방향 적용이다 | 두 파일 모두에서 검증(현행) |
| D-336 | 8/21 | 폐기된 계약 이름의 재유입은 grep 린트가 아니라 **동작 단언**으로 막는다 — `assert "<옛_이름>" not in state` 를 진입점 테스트와 경계 테스트 양쪽에 한 줄씩 둔다 | grep 린트를 실제로 돌려보니 실제 코드 사용 0건 대비 주석·의도적 가드 오탐이 2건이었다(오탐률 2/3). 허용 목록을 유지하는 비용이 얻는 것보다 크다. 동작 단언은 오탐이 없고, 옛 키가 실제로 state 에 실릴 때만 실패한다. contract_fitness 에는 이미 `assert "source_gen_id" not in seen` 이 있었으므로 main_contract 에 한 줄만 추가하면 양쪽이 막힌다 | models/ 전체 grep 린트 테스트 추가 |
| D-337 | 8/21 | 테스트에서 검증 항목을 뺄 때는 "어느 파일이 대신 보는가" 를 docstring 에 명시한다 | test_main_contract.py 에서 source_context 검증을 제거했는데, 근거 없이 지우면 다음 사람이 "왜 이건 안 보나" 를 알 수 없고 다시 추가해 중복이 부활한다. 파일 간 역할 분담(D-335)은 코드에 적혀 있어야 유지된다 — decisions.md 만으로는 코드를 읽는 사람에게 닿지 않는다 | 주석 없이 제거 |

## 변경 이력
> 뒤집힌 결정은 **원래 줄을 지우지 말고** 아래 추가.

| 날짜 | 대상 | 변경 내용 | 사유 |
|------|------|-----------|------|
| — | — | — | — |
| 8/11 | D-016 | email → username | ORM 구현 상태와 맞춤 |
| 8/11 | D-009 | request_id → Idempotency-Key | 서비스 개발 담당 구현 편의 존중 |
| 8/11 | D-0xx | Consultant 응답: proposals 평탄화 → strategy/reasons 유지 | actions를 copy로 합치면 프론트가 전략 카드 개별 렌더링 불가, reasons 의미 유실 | 평탄화 |
| 8/13 | 골든 데이터셋 | 컨설턴트 30문항 → 20문항 | golden_dataset.md v1.0 기준으로 3개 SDP 문항 수 통일 |
| 8/13 | 밀도 등급 | 사용자 노출 → 프롬프트 내부 힌트로만 사용 | 경계값이 임의 근사치라 외부 검증 불가 |
| 8/13 | get_market 시그니처 | (lat,lng,radius) → (lat,lng,radius,industry=None) | 캐시는 업종 무관 원본만 저장, 집계는 호출 시 계산 — 캐시 재사용률 개선(SDP §2.7 원안 대비 담당자 개선안 채택) |
| 8/13 | Contract v0.3 §4.5·§10.4·S-18 | Basic 10/Consultant 50 → Basic 50/Consultant 10 | D-006·D-021과 반전 기재됐던 것을 정정 |
| 8/13 | .env.example | DATABASE_URL 공란(로컬 폴백) → sqlite:///./data/app.db | 서비스·캐시 DB 통합. 단 캐시 테이블 생성 주체는 D-058로 별도 지정 |
| 8/13 | ERD | source_gen_id "FK 없이 값만 저장" → 실제 self-FK | 구현이 더 안전하므로 문서를 코드에 맞춤 |
| 8/13 | D-027 | platform 3종(blog 포함) → 2종(instagram·banner) | Contract v0.3·서비스 Literal·모델 코드 모두 2종으로 수렴 |
| 8/13 | D-019 | 이미지 재생성 1회 원칙을 코드에 반영(MAX_RETRY 공유 해제) | 공유 카운터로 인해 실질 2회 실행되던 것을 정정 |
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
| P-011 | market_cache UNIQUE(lat,lng,radius) 추가 시점 | D7 통합 시 서비스 개발 담당이 DDL 추가(그전까지 upsert로 방어, D-050) | 서비스 개발 담당 | 8/18 |
| P-012 | payments package·status enum 확정 | 임시안 유지, 결제 API 구현 전 확정 | 서비스 개발 담당 | 8/19 |
| P-013 | 이미지 생성 장수·병렬화(3장 직렬 / 상위 1안만 / 3장 병렬) | D6에 1장 실측 후 결정 | 기본 챗봇 담당 | 8/18 |
| P-014 | 벤치마크 RAG 착수 시점 — 미착수 시 Hit Rate@5·MRR 산출 불가 | SDP상 D8, 지연 시 검색 지표를 보고서에서 제외할지 결정 | 전민재 PM | 8/18 |
| P-015 | CLIP 한국어 대응(다국어 CLIP 교체 vs 영문 이미지 프롬프트로 채점) | 영문 프롬프트 안이 비용상 유리 | 기본 챗봇 담당 | 8/19 |
| P-016 | shared 임베딩 래퍼(embed_texts) 제공 시점 | 벤치마크 인덱싱 착수(P-014) 전까지 제공 | 전민재 PM | 8/18 |
| P-017 | models/consult/config.py 재노출 제거 + 각 노드가 shared 직접 import | D7 통합 정리 시 | 컨설턴트 담당 | 8/18 |
| P-018 | 중첩 구조(BasicProposal·ProposalError·ConsultantStrategy·ConsultantAction) extra 정책 | ignore 통일 + 로깅 권고. 현행 strict는 channel_format 화이트리스트에 의존 — clip_score 노출 시 502 | 서비스 개발 담당 | 8/15 |
| P-019 | GenerationResponse.result의 ModelResult union 잔존 처리 | 현행 유지 + 챗봇별 직렬화 확인 테스트 1개 추가 | 서비스 개발 담당 | 8/15 |
| P-020 | 어댑터 배선 시 chatbot_type 단일 소스 확인(요청값 사용) | D4 /generate 구현 PR에서 확인 | 서비스 개발 담당 | 8/15 |
| P-021 | 가게 주소·위치 수정 수단(PATCH /users/me vs 사이드바 입력) | D5 사이드바에 표시만, 수정 API는 D8 | 서비스 개발 담당 | 8/18 |
| P-022 | production 필수 env 검증 범위 — validate_deploy_config가 SESSION_SECRET_KEY·SESSION_COOKIE_SECURE를 검사하는지 확인 | .env.example 그대로 배포 시 기동 실패(크래시 루프) | 서비스 개발 담당 | 8/15 |
| P-023 | status=generating 잔여 행 처리(프로세스 중단 시 크레딧만 차감된 행) | 자동 복구는 미구현, 시연 전 수동 확인 절차로 대체 | 서비스 개발 담당 | 8/21 |
| P-024 | datetime 저장 경로 통일(register_user aware 직접 저장 → _bind_utc 경유) | SQLite에선 결과 동일, 규칙만 통일 | 서비스 개발 담당 | 8/18 |
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
| P-059 | tests/integration/ 을 CI 기본 실행 대상에 포함할지 | RUN_LIVE_SMOKE 미설정 시 LLM 모델 호출 0회라 비용은 없으나, models/consult/main.py 미구현 브랜치에서 빨간불이 난다. 두 챗봇 run() 머지 후 판단(D-296) | 서비스 개발 담당 | 8/21 |
| P-060 | 기본 챗봇(B-) Judge 안정성 파일럿에도 D-298 3계층 기준 적용 | rubric 4항목·25문항이라 환산 SD 기준(0.05)은 동일하게 적용 가능. 본 평가 전 동일 절차 수행 | 기본 챗봇 담당 | 8/21 |
| P-061 | 편차 2 이상 셀이 반복 발생하는 rubric 항목의 문구 재작성 | 현재 0건이라 조치 불필요. 본 평가에서 재발하면 해당 항목의 1점/5점 앵커 문구를 구체화(v2 PDF 채점 앵커 표 기준) | 컨설턴트 담당 | 재발 시 |
| P-062 | actions 개수 계약(min/max)이 strategy 프롬프트·Pydantic·평가 스크립트 세 곳에서 동일한지 확인 | actions_wrong_length 의 기준값이 어디에 정의돼 있는지에 따라 D-301 의 ①/② 분류가 갈린다 | 컨설턴트 담당 | 8/21 |
| P-063 | frontend/api_client.py::generate() 가 옛 Preview 계약({"prompt": ...})을 사용 | 현재 호출하면 422. compose smoke test 가 health() 만 검증해 CI 는 초록불이다. D8 결과 화면 작업 시 실제 GenerateRequest·Idempotency-Key·인증에 맞춰 정리하거나 제거 | 서비스 개발 담당 | 8/22 |
| P-064 | stale generating 복구 후 HTTP 500 반환이 적절한지 | recover_stale_generating 성공 시 _internal_error("stale_generation_recovered") → 500 이다. 사용자가 해야 할 행동은 "새 Idempotency-Key 로 재시도"인데 500 은 그 신호를 주지 못하고 실제 서버 버그와 구분되지 않는다. D8 에러 배너 3종 작업 시 함께 판단 | 서비스 개발 담당 | 8/22 |
| P-065 | ChatbotClient Protocol 의 반환 타입 annotation | `async def generate(...) -> ModelResult` 로 선언돼 있으나 실제 D7 클라이언트는 dict 를 반환하고 서비스가 MODEL_RESULT_ADAPTER 로 검증한다. Mock 만 ModelResult 객체를 돌려준다. D7 실클라이언트 작성 시 시그니처를 실제와 맞춘다 | 서비스 개발 담당 | 8/22 |
| P-066 | GitHub 저장소 설정에서 ruleset/required status check 강제 가능 여부 확인 | 가능하면 D-311 의 수동 절차를 자동화로 대체 | 윤승준 | 8/22 |
| P-067 | asyncio.to_thread 기본 실행자 워커 고갈 대응 | GCP VM(vCPU 4) 기준 워커 8개. 180초 좀비 8개면 이후 /generate 가 최대 3분간 시작조차 못 하는데 /health 는 200 을 돌려줘 겉보기엔 정상이다. 전용 ThreadPoolExecutor 분리 또는 동시 생성 수 제한을 D8 이후 판단 | 서비스 개발 담당 | 8/22 |
| P-068 | warm 상태 실측 p95 기반 타임아웃 재산정 | D-313 으로 콜드 스타트 제거 후 카피 3안 + 이미지 3장 생성 시간을 측정해 `p95 × 1.5` 로 정한다. 골든 데이터셋 §6 의 latency_p95_s 지표 그대로 활용 | 전민재 PM | 8/22 |
| P-069 | 배포 헬스체크가 가중치 사전 로딩을 기다릴 수 있는지 확인 | deploy.sh·CI 의 `--wait-timeout 180` 이 lifespan 로딩 시간을 포함해도 충분한지 검증 | 윤승준 | 8/21 |
| P-070 | actions 5건이 '개수 초과'인지 '0개'인지 내역 확인 | 전부 초과면 절단만으로 LLM 모델 호출 0회로 해결되고, 0개가 섞여 있으면 그만큼만 재생성이 필요하다. D-317 적용 범위가 여기서 갈린다 | 컨설턴트 담당 | 8/21 |
| P-071 | 기존 60문항 실행 결과가 §10.4 결과 파일 형식으로 저장돼 있는지 확인 | 저장돼 있지 않으면 baseline 이 없어 재측정이 필요하다(D-318). `compare_reports.py --validate` 로 헤더 형식을 확인한다 | 컨설턴트 담당 | 8/21 |
| P-072 | OpenAI Structured Outputs(json_schema strict)로 배열 길이 제약을 강제할 수 있는지 확인 | 가능하면 복구 로직 없이 계약을 원천 보장할 수 있다. minItems/maxItems 지원 여부 문서로 확인한 뒤 판단 | 전민재 PM | 8/22 |
| P-073 | 기본 챗봇(B-)에도 동일 유형의 확률적 계약 위반이 있는지 점검 | proposals 3개 고정·suggested_chips 빈 배열도 같은 성격의 제약이다. D-316 분류를 두 챗봇에 동일 적용한다 | 기본 챗봇 담당 | 8/22 |
| P-074 | `models/basic/main.py` 의 필수 키 목록을 공개 상수로 노출할지 | D-322·D-323 으로 테스트는 공개 API 만 쓰게 됐으나, 서비스 개발 담당자가 D7 클라이언트에서 사전 검증하고 싶어질 수 있다. 필요가 실제로 생기면 그때 공개 상수로 승격한다 | 기본 챗봇 담당 | 필요 시 |
| P-075 | `tests/integration/` 의 다른 파일도 비공개 이름 의존이 있는지 점검 | `test_d7_model_boundary.py`(서비스 개발 담당 관리)는 `run()` 만 호출하므로 해당 없음. 앞으로 추가되는 경계 테스트에 D-322 를 적용한다 | 전민재 PM | 8/22 |
| P-076 | 관리 경계를 넘는 PR 의 승인 절차 문서화 | D-324·D-325 를 `docs/directory_structure.md` §7.7 에 반영할지 판단. 현재는 예외 사례가 1건뿐이라 decisions.md 기록으로 충분할 수 있다 | 전민재 PM | 8/22 |
| P-077 | 이번 실패로 실제 소모된 토큰·금액 확인 | context length exceeded 는 요청 거부라 과금이 없을 가능성이 높으나 확인이 필요하다. 팀 디스코드 `!usage` 로 파일럿 재실행 전 1회 확인 후 남은 예산을 재계산한다 | 기본 챗봇 담당 | 8/21 |
| P-078 | 본 평가 스크립트 3종(eval_generation·eval_strategy·거부)이 judge_payload 를 쓰는지 확인 | 파일럿만 고치면 본 평가에서 재발한다(D-329). 각 스크립트가 응답을 프롬프트에 넣는 지점을 전수 확인한다 | 각 담당 | 8/22 |
| P-079 | eval_image.py(CLIP Score)가 이미지 채점을 실제로 담당하는지 확인 | Judge 에서 이미지를 뺐으므로 이미지 품질 측정 경로가 별도로 살아 있어야 §6 지표가 비지 않는다. 미구현이면 SHOULD 로 남길지 판단 | 기본 챗봇 담당 | 8/22 |
| P-080 | models/consult/tests/ 에도 같은 중복이 있는지 점검 | 컨설턴트 진입점 테스트가 서비스↔모델 키 매핑을 함께 보고 있으면 D-335 기준으로 분리한다. P-055·P-056 과 함께 처리 | 컨설턴트 담당 | 8/22 |
| P-081 | D-306 영향 파일 목록의 나머지 2건 반영 확인 | docs/validation_contract.md §8.6-3 문구 수정, models/consult/main.py 가 source_context 를 받지 않는지 확인 — 두 건 모두 CI 로는 안 잡힌다 | 전민재 PM | 8/22 |