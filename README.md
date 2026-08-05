# Codeit Part 4 6팀 프로젝트

생성형 AI를 활용해 소상공인의 광고 콘텐츠 제작을 돕는 서비스입니다.

현재 저장소는 POC에서 검증한 사용자 흐름을 팀 프로젝트 구조로 옮기는 초기 단계입니다.

> 현재 FastAPI·Streamlit 코드와 포트 매핑은 uv, Docker 빌드, 컨테이너 통신 및 외부 접근을 확인하기 위한 임시 스켈레톤입니다. 최종 서비스 요구사항이 확정되면 관련 구현과 API 계약을 교체하거나 제거합니다.

## 빠른 실행

```bash
cp .env.example .env
docker compose up --build
```

- 프론트엔드: `http://localhost:8501`
- 백엔드 헬스체크: `http://localhost:18000/health`
- 백엔드 API 문서: `http://localhost:18000/docs`

현재 `/generate`는 프론트엔드와 백엔드 연결을 확인하기 위한 목 응답을 반환하며 최종 API 계약이 아닙니다.

서비스별 실행환경과 포트는 다음 문서를 확인해주세요.

- [백엔드 안내](backend/README.md)
- [프론트엔드 안내](frontend/README.md)
- [Python 의존성 관리](docs/dependency-management.md)
