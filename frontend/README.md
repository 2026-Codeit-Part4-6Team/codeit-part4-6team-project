# 프론트엔드

Streamlit 기반 사용자 화면 컨테이너입니다. 입력한 광고 요청을 FastAPI 백엔드로 전달하고 생성 결과를 표시합니다.

현재 화면은 Docker 실행과 프론트엔드·백엔드 통신을 직접 확인하기 위한 임시 테스트 UI입니다. 최종 UI 요구사항이 확정되면 교체하거나 제거합니다.

## 컨테이너와 포트

| 항목 | 값 |
| --- | --- |
| Compose 서비스 이름 | `frontend` |
| 컨테이너 내부 포트 | `8501` |
| 호스트 포트 | 기본 `8501`, GCP 확인 시 `80` |
| 사용자 접근 주소 | `http://localhost:8501` |
| 컨테이너 내부 백엔드 주소 | `http://backend:8000` |

브라우저는 호스트 `8501`번으로 접근하고, 프론트엔드 컨테이너는 Compose 내부 네트워크에서 `backend:8000`으로 API를 호출합니다. 호스트의 JupyterHub `8000`번 포트와는 관계가 없습니다.

호스트 포트는 `.env`의 `FRONTEND_PORT`로 변경합니다. 현재 공개 포트는 초기 스켈레톤 확인용입니다.

## 환경변수

| 변수 | 기본값 | 용도 |
| --- | --- | --- |
| `BACKEND_URL` | `http://backend:8000` | 백엔드 API 주소 |

## 실행 및 확인

저장소 루트에서 실행합니다.

```bash
docker compose up --build frontend
```

브라우저에서 `http://localhost:8501`로 접속합니다. `frontend`는 백엔드 헬스체크가 통과한 뒤 시작합니다.

## 현재 구조

```text
frontend/
├── app.py          Streamlit 화면 진입점
└── api_client.py   FastAPI 호출
```
