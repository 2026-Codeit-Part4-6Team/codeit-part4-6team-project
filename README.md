# Codeit Part 4 6팀 프로젝트

생성형 AI를 활용해 소상공인의 광고 콘텐츠 제작을 돕는 서비스입니다.

현재 저장소는 POC에서 검증한 사용자 흐름을 팀 프로젝트 구조로 옮기는 초기 단계입니다.

- [초기 서비스 아키텍처](docs/architecture.md)
- [개발환경 및 의존성 관리](docs/development.md)

## 빠른 실행

```bash
cp .env.example .env
docker compose up --build
```

- 프론트엔드: `http://localhost:8501`
- 백엔드 헬스체크: `http://localhost:18000/health`
- 백엔드 API 문서: `http://localhost:18000/docs`

현재 `/generate`는 프론트엔드와 백엔드 연결을 확인하기 위한 목 응답을 반환합니다.
