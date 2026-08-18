# D5 React Frontend

Figma의 로그인 `3:86`, 회원가입 `3:112`, 대시보드·사이드바 `3:179`를 기준으로 구현한 D5 React 화면입니다. 1440×1024 고정 좌표를 복제하지 않고 색상, 카드 계층과 Sidebar:본문 비율을 반응형 CSS로 재현합니다.

## D5 범위

- 로그인·회원가입과 회원가입 후 자동 로그인
- Session Cookie 유지와 `/users/me` 인증 복원
- Backend UserResponse 기반 가게·무료 잔여·Credit Sidebar
- 컨설턴트·게시물 생성 진입 경로
- 컨설턴트, 마이페이지, 결제 placeholder
- 기존 React POC의 `/generate/estimate`, `/generate` 연결을 게시물 생성 화면에 보존

게시물 생성 내부 화면의 Figma 재설계와 실제 컨설턴트 연결은 D5 이후 범위입니다.

## 로컬 Frontend

```powershell
corepack pnpm install --frozen-lockfile
corepack pnpm test
corepack pnpm typecheck
corepack pnpm build
corepack pnpm dev
```

브라우저 요청은 same-origin `/api`를 사용합니다. Vite 개발 서버와 production frontend container가 `BACKEND_URL`로 proxy하므로 Backend CORS 변경은 필요하지 않습니다.

## Docker Compose 시연

기존 POC와 포트가 겹치지 않도록 실행 환경에 맞는 포트를 지정할 수 있습니다. 아래 값은 예시이며 고정된 배포 주소가 아닙니다.

```powershell
$env:BACKEND_PORT='<backend-port>'
$env:FRONTEND_PORT='<frontend-port>'
$env:APP_ENV='demo'
$env:GEOCODE_FALLBACK_ENABLED='true'
docker compose -p d5-react-frontend up --build -d
```

- Frontend 접속 주소: 실행 환경의 Host와 `FRONTEND_PORT`
- Backend 연결 주소: Compose 내부 `BACKEND_URL` 또는 배포 환경 설정값

개발자 계정은 앱 시작 때 자동 생성하지 않습니다. 필요하면 별도 `python -m backend.demo_seed` 명령을 명시적으로 실행합니다.
