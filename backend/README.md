# 백엔드

FastAPI 기반 API 컨테이너입니다. 서비스 기반, 인증, Session, 회원가입 지오코딩과 목 생성 API를 제공합니다.

생성 관통 API와 실제 모델 연동은 D4 이후 마일스톤에서 구현합니다. 현재 `/generate`는 D4 전환 전까지 유지하는 Preview API입니다.

## 컨테이너와 포트

| 항목 | 값 |
| --- | --- |
| Compose 서비스 이름 | `backend` |
| 컨테이너 내부 포트 | `8000` |
| 호스트 포트 | `18000` |
| 프론트엔드에서 접근하는 주소 | `http://backend:8000` |
| 호스트에서 확인하는 주소 | `http://localhost:18000` |

호스트의 `8000`번 포트는 VM에 설치된 JupyterHub가 사용합니다. 백엔드는 호스트 `18000`번을 컨테이너 `8000`번에 연결하므로 포트가 충돌하지 않습니다.

`18000`번은 초기 스켈레톤의 외부 접근을 직접 확인하기 위한 임시 포트입니다. 실제 서비스 통합 및 운영 배포에서는 제거하거나 프록시를 통한 내부 접근으로 변경합니다.

## 엔드포인트

| 메서드 | 경로 | 용도 |
| --- | --- | --- |
| `GET` | `/health` | 컨테이너 상태 확인 |
| `POST` | `/auth/register` | 사용자명 기반 회원가입과 주소 지오코딩 |
| `POST` | `/auth/login` | Session 로그인 |
| `POST` | `/auth/logout` | Session 로그아웃 |
| `GET` | `/users/me` | 인증 사용자와 사용량 상태 조회 |
| `POST` | `/generate` | 목 광고 콘텐츠 생성 |
| `GET` | `/docs` | OpenAPI 문서 |

## 실행 및 확인

저장소 루트에서 실행합니다.

```bash
docker compose up --build backend
curl http://localhost:18000/health
```

Backend 컨테이너는 시작 시 `python -m backend.init_db`를 먼저 실행합니다. 초기화가 실패하면 API 프로세스가 시작되지 않아 Compose healthcheck가 통과하지 않습니다. 수동으로 초기화할 때는 아래 명령을 사용합니다.

```bash
docker compose run --rm backend python -m backend.init_db
```

서비스 초기화 명령은 `users`, `payments`, `generations`, `waiting_copies` 네 테이블만 관리합니다. 모델 캐시 테이블은 별도 초기화 책임을 갖습니다.

## 현재 구조

```text
backend/
├── main.py              애플리케이션 생성과 라우터 등록
├── schemas.py           요청·응답 스키마
├── routers/             HTTP 엔드포인트
└── services/            생성 유스케이스
```

LangGraph, DB, 추론 서버 관련 디렉터리는 담당 기능과 계약이 확정된 뒤 추가합니다.
