# React 최소 생성 폼 POC

실제 FastAPI Session Cookie와 `/generate/estimate`, `/generate` 계약을 확인하기 위한 Vite·React·TypeScript 비교 브랜치입니다. `/api` 요청은 Vite proxy를 통해 `BACKEND_URL`로 전달하므로 Backend CORS 변경은 없습니다.

```powershell
pnpm install --frozen-lockfile
pnpm test
pnpm build
pnpm dev
```

로컬 Backend 기본 주소는 `http://127.0.0.1:18000`, Compose에서는 `http://backend:8000`입니다.
