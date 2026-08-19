# 소프트웨어 개발 계획서 (SDP)

## 서비스 개발 담당 전용: 매출부스터 통합 플랫폼

| 항목 | 내용 |
| --- | --- |
| 문서 버전 | SDP Service v2.0 |
| 기준일 | 2026-08-18 |
| 원래 개발 기간 | 2026-08-10 ~ 2026-08-24 |
| 담당 | 서비스 개발 담당 1명 |
| 현재 상태 | D1~D3 구현 완료, D4 리뷰·머지 대기, D5~D6 React UI Draft PR 진행 |

이 문서는 개발 시작 전 계획서가 아니라, 최신 의사결정과 D1~D10 계약을 기준으로 현재 구현 상태와 남은 작업을 관리하는 실행 문서다. 완료되지 않은 기능은 완료된 것처럼 기록하지 않는다.

## 1. 기준과 우선순위

### 1.1 문서 우선순위

정책·수치·최종 결정은 `docs/decisions.md`를 따른다.

API·DTO·DB 형식과 소유 경계는 D1~D10 구현계약서를 따른다.

마일스톤 계획은 실행 순서와 완료 기준을 정의한다. 결정 로그와 충돌하는 낡은 계획 문구는 이 SDP에서 최신 결정에 맞춰 정정한다.

코드와 PR은 구현 증거다. 코드가 계약과 다르면 임의로 정상 처리하지 않고 Gate 또는 정합성 수정 대상으로 기록한다.

### 1.2 상태 표기

| 상태 | 의미 |
| --- | --- |
| 완료 | 구현과 관련 검증 증거가 있음 |
| 리뷰·머지 대기 | 구현은 끝났지만 PR 리뷰 또는 선행 브랜치 머지가 남음 |
| 연동 대기 | 계약 경계는 준비됐지만 실제 외부 구현이 아직 연결되지 않음 |
| Gate | 외부 결정이나 계약 확정 없이는 완료 판정할 수 없음 |
| 후속 | 현재 마일스톤에서 의도적으로 제외한 작업 |

### 1.3 확정 정책

- 서비스명은 `매출부스터`다.
- 일일 무료 사용량은 Basic과 Consultant가 공유하는 10회다.
- Basic 생성 비용은 50 Credit, Consultant 생성 비용은 10 Credit이다.
- Credit의 Single Source는 `users.credits`다.
- 로그인 식별자는 `username`이다.
- 중복 생성 방지는 `Idempotency-Key`와 request hash를 함께 사용한다.
- 플랫폼은 `instagram`과 `banner`를 사용하며 `blog`는 제외한다.
- Frontend는 Credit, 무료 사용량, StoreContext를 자체 계산하거나 요청 body에 직접 넣지 않는다.
- ModelResult 성공 분기는 `chatbot_type`으로 명시한다. Smart Union 추론에 의존하지 않는다.
- 모델 호출은 동기 방식이며 서비스 timeout은 60초다. 모델 호출 전 DB write transaction을 종료한다.

## 2. 서비스 책임과 소유 경계

### 2.1 서비스 개발 담당 소유

- React Frontend와 공통 UI Shell
- FastAPI 앱 조립과 Public API
- 인증·Session Cookie 경계
- SQLAlchemy/SQLite 서비스 테이블
- Usage/Credit Reservation, settle, compensation
- Generation 상태와 Idempotency orchestration
- Frontend↔Service DTO 계약
- Mock Chatbot Client와 실제 Client 교체 경계
- Docker Compose 및 CI/CD 연동 검증

### 2.2 다른 담당자 소유

- `models/basic/`: Basic 광고 생성 파이프라인
- `models/consult/`: Consultant 상권 분석·전략 파이프라인
- `models/shared/`: 공통 LLM wrapper와 공통 모델 설정
- `validation/`: PM 소유 검증 함수와 규칙
- `cache/`: Consultant 소유 Cache ORM/DDL/bootstrap
- `shared_data/`: PM/Consultant가 관리하는 데이터 자산
- GCP VM 운영과 실제 production deploy 승인

서비스는 `market_cache`, `review_cache`, `banned_keywords`의 데이터 적재와 모델 내부 판정 로직을 소유하지 않는다. 필요한 API/DDL 경계만 계약하고 import 또는 Public API로 연결한다.

## 3. 현재 마일스톤 상태

| 단계 | 현재 판정 | 근거 및 남은 조건 |
| --- | --- | --- |
| D1 서비스 기반 | 완료 | DB/DTO/Mock/API 기반과 테스트 구축 |
| D2 인증·지오코딩 | 완료 | username Session, bcrypt, geocoding/fallback 계약 및 검증 |
| D3 사용량·과금 | 완료 | 무료/Credit Reservation, Estimate, rollback/settle, 402 |
| D4 생성 오케스트레이션 | 리뷰·머지 대기 | D4 PR 구현·회귀 검증 완료, PR 리뷰와 후속 계약 반영 대기 |
| D5 React 첫 화면 | 구현 완료·리뷰·머지 대기 | `feat/d5-react-frontend`, Draft PR #120 |
| D6 챗봇 입력 흐름 | UI 구현 완료·리뷰·머지 대기 | `feat/d6-react-chat-input`, Draft PR #119 |
| D7 실제 챗봇 연동 | Gate | 실제 entrypoint, Provider 설정, 응답 assembly 확정 필요 |
| D8 결과 승인·게시 | Gate | 동의·publish·이미지 저장·CAS 계약 연결 필요 |
| D9 마이페이지·결제 | Gate | history/payment API와 catalog 정책 확정 필요 |
| D10 통합 안정화 | 후속 | D7~D9 완료 후 E2E·운영 검증 |

### 3.1 완료 판정 근거

| 단계 | 현재 증거 | 아직 필요한 것 |
| --- | --- | --- |
| D1 | 서비스 DB/DTO/Mock 기반과 테스트 코드 | 최신 main 기준 전체 회귀 재확인 |
| D2 | username Session, bcrypt, geocoding/fallback 구현 및 테스트 | Provider transport Gate 확인 |
| D3 | Usage/Credit Reservation, Estimate, 402, rollback/settle 테스트 | D4 merge 후 계약 회귀 확인 |
| D4 | PR #103/#104 구현·회귀 검증과 D4 보고서 | 리뷰 후 merge, D7 계약 정합성 반영 |
| D5 | React 화면·Sidebar, Draft PR #120, Vitest 27, TypeScript, Docker healthcheck | D4 merge 후 main base 재정렬 |
| D6 | React Basic/Consultant UI, Draft PR #119, Vitest 31, TypeScript, Docker healthcheck | 실제 모델 응답과 정책 상태 연동 |

## 4. D1~D6 실행 내용

### 4.1 D1: 서비스 기반

D1은 모델 담당자가 완성되기 전에도 서비스 개발을 진행할 수 있도록 Public DTO, Model DTO, DB, Mock 경계를 만들었다.

서비스 소유 테이블은 `users`, `payments`, `generations`, `waiting_copies` 네 개다. Cache 테이블은 서비스 `init_db.py`의 경계에 병합하지 않는다.

주요 기반은 다음과 같다.

- FastAPI 앱 조립
- SQLAlchemy Engine/Session
- SQLite foreign key와 transaction 경계
- Pydantic Public/Model schema
- Mock Chatbot Client
- `/health`와 readiness 검증
- 개발 DB와 테스트 DB 격리

### 4.2 D2: 인증·지오코딩

- `username` 기반 회원가입·로그인·로그아웃
- bcrypt password hash
- signed Session Cookie
- Session에는 `user_id`만 저장
- Session 최대 연령 8시간
- `GET /users/me` 인증 복원
- 주소 등록 시 geocoding과 좌표 저장
- Provider 장애 fallback은 development/demo에서만 허용
- 주소 미검색은 422, Provider 장애는 503

실제 Provider transport의 세부 endpoint/header/응답 경로가 계약에서 Gate로 남아 있으면, SDP는 해당 transport를 완료로 주장하지 않는다.

### 4.3 D3: 사용량·과금

D3는 무료 사용량과 Credit Reservation을 서비스 로직으로 분리했다.

- Basic/Consultant 무료 사용량 공유
- KST 자정 기준 lazy reset
- 무료 사용량 우선 사용
- 무료 소진 후 Basic 50 / Consultant 10 Credit 차감
- Credit 부족 시 402
- Estimate는 상태를 변경하지 않음
- Reservation 성공 후 상위 Use Case가 commit
- 모델 실패/차단/timeout 시 rollback 또는 compensation
- Reservation과 compensation은 DB conditional update/CAS 기반

### 4.4 D4: 생성 오케스트레이션

D4의 생성 흐름은 다음과 같다.

```text
StoreContext 검증
  → Generation INSERT(idempotency_key, request_hash)
  → 무료/Credit Reservation
  → generating commit
  → transaction 밖에서 모델 호출
  → 새 transaction에서 결과 저장과 settle/compensation
```

동일 Key와 동일 body는 기존 결과를 replay하고, 동일 Key와 다른 body는 409로 거부한다. `source_gen_id`가 있으면 서비스가 동일 사용자 Consultant `done` 결과를 검증해 내부 `source_context`를 구성한다.

D4는 구현과 회귀 검증이 진행됐지만 PR 리뷰·후속 정합성·머지가 남아 있으므로 전체 프로젝트 완료로 표시하지 않는다.

### 4.5 D5: React 첫 화면

D5의 실제 Frontend 기준은 Streamlit이 아니라 React다. Streamlit은 이전 POC 또는 비교 자료로만 취급한다.

D5 화면 범위:

- 로그인
- 회원가입
- 인증 복원
- Dashboard
- 공통 Sidebar
- 게시물 생성 및 Consultant 진입 route
- 반응형 모바일 메뉴

Figma 기준 프레임은 로그인 `3:86`, 회원가입 `3:112`, Dashboard/Sidebar `3:179`다. D5는 픽셀 좌표 복제가 아니라 색상·카드 계층·상대 비율·반응형 동작을 재현한다.

실제 D5 브랜치와 Draft PR은 D4 선행 작업 위에 존재하며, D4 merge 후 base를 `main`으로 정리한다.

### 4.6 D6: 챗봇 입력 흐름

Basic은 `첫 메시지`와 예시 chip을 중심으로 입력한다. 광고 목적·타깃·가격대·가게 강점은 선택 상세 영역으로 접어 초기 화면의 밀도를 낮춘다.

Consultant는 질문 하나와 예시 chip을 중심으로 입력한다. 가게명·업종·주소·좌표는 Frontend가 다시 받지 않고 Backend StoreContext를 사용한다. 초기 `extra`는 null로 조립할 수 있으며 정보 부족 시 clarification을 후속 입력으로 받는다.

결과 화면은 Basic proposal 3 slot과 Consultant strategy/actions/reasons/sources/suggested_chips를 구분한다. Basic 3 slot은 부분 실패에도 위치를 유지한다. Consultant 카드 UI는 이 응답 구조를 소비할 준비가 된 Mock/prototype 상태이며, 모델 state를 nested Public response로 조립하는 작업은 D7 Gate다.

현재 후속 메시지는 화면 state 기반 prototype이다. 영구 메시지 로그와 채팅방 저장은 별도 대화 계약이 확정된 뒤 진행한다.

## 5. D7~D10 실행 계획과 Gate

### 5.1 D7: 실제 챗봇 연동

D7 완료 조건:

- `CHATBOT_MODE=actual` wiring
- Basic/Consultant 실제 entrypoint의 callable path와 signature 확정
- `ActualChatbotClient`가 Mock fallback 없이 명시적 실패 처리
- 모델 요청은 dict in/dict out 경계 유지
- 모델 결과를 `chatbot_type`으로 명시 검증
- Consultant 결과를 nested `strategy` 응답으로 assembly
- `title`, `sources`, `suggested_chips` fallback 정책 반영
- ModelResult를 Service Public schema로 검증하는 계약 테스트
- 실제 응답이 React UI까지 표시

D7에서 함께 닫아야 하는 최신 결정 항목은 D-179, D-204~D-217이다. 특히 `models/consult/main.py::run()`과 `assemble_response()`의 nested strategy 조립, `classify_llm_error` 공통 위치, title/sources/suggested_chips fallback, blocked reason/message 정규화, Basic/Consultant 별도 계약 테스트를 완료 기준에 포함한다. D-217에 따라 계약 테스트가 red인 상태는 정상적인 사전 경고가 될 수 있으며, 이를 테스트 완화로 해결하지 않는다.

모델명·Provider는 `models/shared/config.py`와 환경변수 단일 소스를 따르며, Frontend 환경설정은 이를 자체 결정하지 않는다. 최종 Provider/모델이 확정되기 전에는 실제 업체명을 UI 계약으로 고정하지 않는다.

### 5.2 D8: 과금 동의·결과 승인·게시

D8 완료 조건:

- 유료 Estimate 결과를 동의창에서 표시
- 사용자 확인 전 유료 Generate 자동 호출 금지
- 동기 모델 호출 중 대기 화면과 timeout/error 표시
- Basic proposal 3 slot과 partial failure 표시
- 승인 대상 선택
- `done → published` compare-and-set
- `POST /generations/{id}/publish`
- publish 시 이미지 signature와 5 MiB 제한 검증
- 승인 전 `image_b64`는 result storage에 저장하지 않음
- 재생성·reask는 새 Estimate와 새 Idempotency-Key 사용

D8는 P-004 재생성 시 동의창 재노출, P-013 이미지 생성 장수·병렬화, P-018 중첩 모델 extra 정책, D-180 validation 함수 실구현 증거를 함께 확인한다.

### 5.3 D9: 마이페이지·결제

D9는 다음 Gate가 닫힌 뒤 시작한다.

- Payment package별 amount/credits
- Payment status enum
- 중복 결제 방지 정책
- Payment catalog SSOT 위치
- 데이터 보관·삭제 정책

추가로 P-003 데이터 보관·삭제, P-012 Payment package/status enum과 catalog, P-026 `alternative`·`law` 노출 여부를 Gate로 유지한다.

Gate 이후 구현 범위:

- `GET /users/me/summary`
- `GET /generations`
- `GET /generations/{id}`
- `POST /payments`
- MyPage summary/history/detail
- BillingPage package 선택과 mock 결제

Frontend는 history와 Credit을 자체 합산하지 않고 서버 계산값을 표시한다.

### 5.4 D10: 통합 안정화

D10은 D7~D9 완료 후 다음을 수행한다.

- Basic/Consultant 실제 응답 E2E
- 회원가입 → 로그인 → 생성 → 과금 → 결과 → 승인 → 이력
- 402/409/422/429/5xx/503/504 오류 흐름
- same-key replay와 stale generating recovery
- Sidebar/UserResponse/MyPage Credit 정합성
- 반응형 Desktop/Mobile 검증
- Docker Compose local integration
- production deploy configuration validation

Production configuration은 P-022의 Session Secret/Secure Cookie 필수값 검증 여부를 별도로 확인해야 한다. 현재 로컬 Docker healthcheck 통과만으로 production configuration 검증 완료를 주장하지 않는다.

GCP VM 배포 실행은 Infrastructure 담당과 수동 승인 범위이며, 로컬 Compose healthcheck 통과만으로 production deploy 완료를 주장하지 않는다.

## 6. API와 데이터 경계

### 6.1 현재/확정 API

| 영역 | Endpoint | 상태 |
| --- | --- | --- |
| 인증 | `POST /auth/register` | D2 완료 |
| 인증 | `POST /auth/login` | D2 완료 |
| 인증 | `POST /auth/logout` | D2 완료 |
| 사용자 | `GET /users/me` | D2 완료 |
| 생성 | `POST /generate/estimate` | D3 완료 |
| 생성 | `POST /generate` | D4 구현·리뷰 대기 |
| 사용자 | `GET /users/me/summary` | D9 Gate |
| 이력 | `GET /generations` | D9 Gate |
| 이력 | `GET /generations/{id}` | D9 Gate |
| 결제 | `POST /payments` | D9 Gate |
| 게시 | `POST /generations/{id}/publish` | D8 Gate |

기존 SDP의 “FastAPI 라우터 12개” 표현은 현재 구현·계약 상태와 맞지 않으므로 API별 상태로 관리한다.

### 6.2 Public Request 원칙

Frontend가 보내는 생성 내용은 `chatbot_type`, `question`, `platform`, `extra`, `source_gen_id` 범위다. Basic은 `platform=instagram|banner`, Consultant는 `platform=null`이다. `extra`는 `purpose`, `price_range`, `target_age`, `strength`, `clarification` 다섯 필드만 사용한다. `user_id`, StoreContext, Credit/free 상태, Consultant 전략 JSON을 Frontend body에서 받지 않는다.

`GenerateRequest`에는 Estimate에서 확인한 `max_accepted_credits`를 추가한다. 실제 비용이 승인 상한보다 크면 차감하지 않고 409를 반환한다.

### 6.3 오류 원칙

서비스 오류 envelope은 `code`, `message`를 필수로 하고 필요한 경우 `required`, `current` 같은 부가 필드를 추가한다. Frontend는 내부 stack trace, API key, password, Cookie를 표시하지 않는다.

Policy message는 Model/Validation 결과를 Service가 임의로 다시 쓰지 않고 계약된 원문을 전달한다.

## 7. 검증 상태와 증거

### D1~D4

- D4 보고서 기준 Service 관련 테스트와 회귀 검증 존재
- D4 PR은 리뷰·후속 반영·merge 대기
- ModelResult adapter, transaction, reservation, compensation, stale recovery 테스트 존재

### D5~D6

- D5 React Draft PR: `#120`
- D6 React Draft PR: `#119`
- D5/D6 Frontend test와 TypeScript 검증 통과
- Docker Frontend/Backend build 및 healthcheck 통과
- 실제 Model Provider·D9 history/payment·D8 publish는 미연동

검증 성공은 해당 범위의 테스트와 build를 의미하며, 후속 마일스톤 완료를 의미하지 않는다.

## 8. 위험과 대응

| 위험 | 대응 |
| --- | --- |
| D4 Contract 변경으로 D5/D6 payload/response drift | D4 merge 후 Frontend contract 재검증 및 Draft PR base 정리 |
| Model entrypoint/response assembly 미확정 | D7 Gate로 분리하고 실제 callable/signature를 먼저 Freeze |
| Basic 3 slot 또는 image 정책 불일치 | 3 slot 유지, partial error 표시, image storage와 publish 경계 분리 |
| Payment catalog 미확정 | D9 Gate 전 가격/크레딧 숫자를 UI에 확정값으로 표시하지 않음 |
| 영구 채팅 로그 요구 확장 | D7/D9 전에 conversation/message 저장 단위를 별도 결정 |
| Production 환경 설정 누락 | `validate_deploy_config.py`, Compose config, manual deploy approval로 검증 |
| Stacked branch ancestry 혼잡 | 부모 PR merge 후 child base를 `main`으로 변경하고 순차 merge |

## 9. 다음 실행 순서

1. D4 리뷰·후속 수정·merge
2. D4 merge 후 D5 Draft PR base를 `main`으로 정리
3. D5 리뷰·merge
4. D6 Draft PR base를 `main`으로 정리 후 리뷰·merge
5. D7 actual wiring과 Consultant response assembly
6. D8 consent/publish
7. D9 history/payment Gate 확정 및 구현
8. D10 E2E와 production deploy 검증

## 10. 완료 정의

전체 SDP 완료는 다음 조건을 모두 만족해야 한다.

- D1~D4 Service 구현과 리뷰·검증 완료
- D5/D6 React UI와 계약 정합성 완료
- D7 실제 Basic/Consultant 응답이 UI까지 연결
- D8 유료 동의·결과 승인·publish 완료
- D9 summary/history/payment Gate와 구현 완료
- D10 통합 E2E와 Docker/production configuration 검증 완료
- 모든 미확정 Gate가 결정 로그와 계약에 반영됨
