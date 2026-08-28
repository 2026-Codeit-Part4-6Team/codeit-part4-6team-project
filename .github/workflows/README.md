# CI/CD 운영 안내

## 현재 범위

- CI는 `main` 대상 PR에서 Python 테스트와 Docker Compose 기반 서비스 기동을 검증합니다.
- CD는 백엔드와 프론트엔드 이미지만 Artifact Registry에 저장하고 GCP VM에 배포합니다.
- CD는 `main` 병합 후 사용자가 Actions 화면에서 수동으로 실행합니다.
- JupyterHub, 모델 실험 환경, Triton, 모델 가중치는 현재 배포 대상이 아닙니다.
- 배포 이미지는 `latest`가 아니라 Git 커밋 SHA로 식별합니다.

## 워크플로 트리거

`ci.yml`은 `main` 대상 PR에서 자동 실행합니다. 현재 저장소 플랜에서는 required status check를
강제할 수 없으므로, `Python tests`, `Deployment assets`, `Compose smoke test`가 모두 통과했는지
리뷰어가 확인한 뒤 병합합니다.

`deploy.yml`은 Push로 실행되지 않습니다. 워크플로가 기본 브랜치에 병합된 뒤 GitHub의
`Actions` → `Deploy` → `Run workflow`에서 `main`을 선택하고 확인 항목을 체크해 실행합니다.
GitHub 수동 실행 워크플로는 기본 브랜치에 파일이 있어야 하므로 PR 단계에서는 CI만 검증합니다.

CLI에서는 다음과 같이 실행할 수 있습니다.

```bash
gh workflow run deploy.yml --ref main -f confirm_deploy=true
gh run watch
```

시연용 배포는 production CD와 분리된 `deploy-demo.yml`을 수동 실행합니다. 워크플로의
`source_ref`에 통합 브랜치 또는 커밋을 지정하며, `main`은 시연용 배포 대상으로 허용하지
않습니다.

CD는 애플리케이션 테스트를 다시 수행하지 않습니다. PR CI를 통과한 코드만 `main`에 병합되도록
Branch ruleset을 구성하고, CD에서는 배포 대상·설정·인증·헬스체크만 검증합니다.

## CI 작업 명세

### Actual model boundary smoke (E2E 사전 점검)

실제 Basic·Consultant 모델 브랜치를 통합한 workspace에서 E2E를 시작하기 전에 담당자가
아래 게이트를 1회 실행하고 결과를 E2E 결과서에 기록합니다. 일반 PR CI에서는 실제 모델과
API 비용을 사용하지 않도록 실행하지 않습니다.

```bash
RUN_MODEL_BOUNDARY_SMOKE=1 uv run --locked --all-groups pytest \
  tests/integration/test_d7_model_boundary.py -q
```

게이트가 실패하면 화면 E2E를 진행하지 않고 모델 entrypoint·패키징·환경변수를 먼저 정리합니다.

CI는 `main` 대상 PR의 코드와 컨테이너 구성이 실행 가능한지 검증합니다. GitHub Runner의
임시 환경에서만 실행하며 Artifact Registry, GCP VM, JupyterHub를 변경하지 않습니다.

```text
Pull Request
├── Python tests
├── Deployment assets
└── Compose smoke test
```

### Python tests

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | PR 코드 Checkout | 대상 커밋 Checkout 성공 |
| 2 | Python `3.11`, uv `0.11.32` 설정 | 고정 버전 설치 성공 |
| 3 | `uv sync --locked --all-groups` | `uv.lock` 변경 없이 의존성 설치 성공 |
| 4 | `uv run --locked --all-groups pytest` | 전체 테스트 통과 |
| 5 | `uv run --locked --group dev ruff check .` | Ruff 검사 통과 |

테스트에서는 공용 `TestClient` fixture를 사용해 클라이언트를 명시적으로 종료합니다. 이에 따라
Windows와 Linux 모두 테스트 통과 후 `pytest` 프로세스가 정상 종료되어야 합니다.

### Deployment assets

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | 예시 `.env` 준비 | 배포 설정 검증용 환경 파일 생성 |
| 2 | `compose.deploy.yaml` 해석 | 예시 이미지 경로로 Compose 설정 검증 성공 |
| 3 | `scripts/deploy.sh` 구문 검사 | `bash -n` 통과 |

이 Job은 Registry나 VM에 접근하지 않고, 배포 자산이 `main`에 병합된 뒤 처음 실패하는 상황을
줄이기 위한 정적 사전 검사만 수행합니다.

### Compose smoke test

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | `docker compose config --quiet` | Compose 설정 해석 성공 |
| 2 | 백엔드·프론트엔드 이미지 빌드 및 실행 | 두 컨테이너가 healthy 상태 |
| 3 | 백엔드 `/health` 호출 | HTTP 200 및 `{"status": "ok"}` 반환 |
| 4 | 프론트엔드 `/_stcore/health` 호출 | HTTP 200 반환 |
| 5 | 프론트엔드 컨테이너에서 `BACKEND_URL`로 `/health` 호출 | Compose 내부 연결 및 `{"status": "ok"}` 확인 |
| 6 | 테스트 스택 정리 | 성공·실패와 관계없이 컨테이너와 임시 볼륨 제거 |

세 Job이 모두 성공해야 CI 통과로 판단합니다. 실패 시 관련 Job의 로그를 확인하며, Compose 실패
시에는 컨테이너 상태와 최근 로그를 자동 출력합니다. CI 실패는 PR 병합만 차단하고 실행 중인 VM
서비스에는 영향을 주지 않습니다.

### Actual model boundary smoke (E2E 사전 점검)

실제 Basic·Consultant 모델을 합친 통합 workspace에서는 E2E 시작 직전에 모델 경계 smoke를
수동으로 실행합니다. 일반 PR CI에서는 모델 호출 비용과 가중치 다운로드를 피하기 위해 실행하지
않으며, 실행자는 통합 테스트 담당자가 담당 브랜치와 로그를 함께 공유합니다.

```bash
RUN_MODEL_BOUNDARY_SMOKE=1 uv run --locked --all-groups \
  pytest tests/integration/test_d7_model_boundary.py -q
```

이 smoke가 통과하고 backend/frontend healthcheck가 healthy인 상태를 1차 E2E 진입 조건으로
삼습니다. 실패하면 E2E 결과서에 모델 entrypoint·환경변수·가중치 캐시 상태를 먼저 기록합니다.

## CD 작업 명세

CD는 CI를 통과해 `main`에 병합된 커밋을 이미지로 만들고 GCP VM에 배포합니다. 자동 Push
트리거는 사용하지 않으며 사용자가 수동 확인 항목을 선택한 경우에만 시작합니다.

```text
Run workflow
→ Deployment preflight
→ Build and push backend/frontend
→ Deploy to GCP VM
→ Public health check
```

### Deployment preflight

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | 실행 브랜치 확인 | `refs/heads/main`과 일치 |
| 2 | 수동 배포 확인 | `confirm_deploy=true` |
| 3 | Repository Variables 확인 | 필수 GCP·VM 설정값 존재 및 안전한 형식 검증 |
| 4 | `compose.deploy.yaml` 검증 | 예시 `.env`와 커밋 SHA로 설정 해석 성공 |

이 단계는 외부 자원을 변경하지 않습니다. 조건이 맞지 않으면 이미지 빌드 전에 종료합니다.

### Build and push

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | WIF로 GCP 인증 | 단기 Access Token 발급 성공 |
| 2 | Artifact Registry 로그인 | Docker 인증 성공 |
| 3 | backend/frontend 병렬 빌드 | 두 Dockerfile 빌드 성공 |
| 4 | 커밋 SHA 태그로 Push | Registry에 두 이미지 저장 |

생성되는 이미지 이름은 다음과 같습니다.

```text
{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/backend:{GIT_SHA}
{REGION}-docker.pkg.dev/{PROJECT}/{REPOSITORY}/frontend:{GIT_SHA}
```

한 이미지라도 빌드 또는 Push에 실패하면 VM 배포 Job은 시작하지 않습니다.
WIF 인증은 작업공간에 자격 증명 파일을 생성하지 않으며, `gha-creds-*.json` 패턴은
`.dockerignore`에서도 제외해 Docker 빌드 컨텍스트 유입을 방지합니다.

### Deploy to GCP VM

| 순서 | 작업 | 완료 조건 |
| ---: | --- | --- |
| 1 | Production Secret으로 SSH 설정 | 개인키와 검증된 호스트 키 적용 |
| 2 | 배포 파일 업로드 | Compose 파일, 예시 환경 파일, 배포 스크립트 전송 |
| 3 | VM 서비스 계정으로 Registry 인증 | Metadata Server의 단기 Token 발급 성공 |
| 4 | 데이터 디렉터리 사전 검사 | Compose가 해석한 경로 생성 및 쓰기 가능 |
| 5 | 커밋 SHA 이미지 Pull | backend/frontend 이미지 다운로드 성공 |
| 6 | 고정 Compose 프로젝트 재기동 | 두 컨테이너가 healthy 상태 |
| 7 | 프론트엔드→백엔드 내부 생성 요청 | `BACKEND_URL` 연결 및 `completed` 상태 확인 |
| 8 | 외부 프론트엔드 헬스체크 | `PUBLIC_HEALTHCHECK_URL` 성공 응답 |
| 9 | 이전 배포 이미지 정리 | 현재 SHA와 직전 공통 SHA를 남기고 오래된 앱 이미지만 제거 |

CD는 SSH 연결 직전에도 Repository Variables를 다시 검증합니다. 배포 경로, SSH 사용자, 이미지
경로 등 원격 명령에 전달되는 값은 허용된 형식만 통과합니다.

CD는 VM의 실제 `.env`를 덮어쓰지 않으며 호스트에 마운트된 데이터 디렉터리를 유지합니다.
JupyterHub, DB, Triton, 모델 가중치는 시작·종료·교체하지 않습니다. 내부 생성 요청과 외부
헬스체크까지 성공해야 배포 완료로 판단합니다. 성공 후에는 이 앱의 backend/frontend 이미지만
정리하며 현재 이미지와 직전 롤백용 이미지를 보존합니다. 현재는 실패 시 자동 롤백하지 않습니다.

내부 생성 요청은 현재 Python 기반 Streamlit 스켈레톤에 맞춘 검사입니다. React 이미지로 교체할
때는 프론트엔드 런타임과 API 진입점에 맞게 검사 명령도 함께 변경합니다.

## 시연용 CD

시연용 CD는 동일한 Artifact Registry와 GCP VM을 사용하되 production 배포와 별도의 Compose
프로젝트·디렉터리를 사용합니다. 포트는 E2E 시나리오와 맞추기 위해 frontend 8501, backend
18000을 사용하므로 두 스택을 동시에 실행하지 않습니다.

```text
Workflow: .github/workflows/deploy-demo.yml
VM path: /srv/team6/demo
Compose project: team6-demo
Compose file: compose.demo.yaml
```

시연용 VM에는 실제 비밀값을 포함한 `/srv/team6/demo/.env`를 미리 만들고,
`.env.demo.example`을 참고해 다음 값을 사용합니다.

```dotenv
APP_ENV=demo
CHATBOT_MODE=actual
DEMO_ACCOUNTS_ENABLED=true
DEMO_PAYMENT_ENABLED=true
FRONTEND_PORT=8501
BACKEND_PORT=18000
```

Demo CD는 `VM_SSH_PRIVATE_KEY`와 `VM_SSH_KNOWN_HOSTS`를 GitHub `demo` Environment에서
읽습니다. production Environment의 비밀값과 분리하고, VM의 실제 `.env`는 업로드하거나
덮어쓰지 않습니다. 결제는 PG 연동이 없는 시연용 Credit 충전이며 실제 금전 거래를 수행하지
않습니다.

시연 종료 후에는 demo 스택만 내립니다.

```bash
docker compose -p team6-demo \
  --env-file /srv/team6/demo/.env \
  -f /srv/team6/demo/compose.demo.yaml down
```

## Main Branch 병합 정책

- Require a pull request before merging
- 병합 전 확인할 검사: `Python tests`, `Deployment assets`, `Compose smoke test`
- 현재 저장소 플랜에서는 required status check를 강제하지 않으므로 리뷰어가 검사 결과를 확인
- 팀 운영 정책상 가능하면 직접 Push를 제한

## GitHub Repository Variables

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `GCP_PROJECT_ID` | `your-gcp-project` | GCP 프로젝트 ID |
| `GCP_REGION` | `us-central1` | Artifact Registry 리전 |
| `ARTIFACT_REGISTRY_REPOSITORY` | `team6-app` | Docker 저장소 이름 |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../providers/...` | GitHub Actions WIF Provider |
| `GCP_SERVICE_ACCOUNT` | `github-actions@....iam.gserviceaccount.com` | 이미지 Push 서비스 계정 |
| `VM_HOST` | `203.0.113.10` | 배포 대상 VM 주소 |
| `VM_SSH_USER` | `deploy` | 배포용 Linux 계정 |
| `VM_DEPLOY_PATH` | `/srv/team6/app` | 배포 파일과 서버 `.env` 위치 |
| `COMPOSE_PROJECT_NAME` | `team6-app` | 고정 Compose 프로젝트 이름 |
| `PUBLIC_HEALTHCHECK_URL` | `http://203.0.113.10:8501/_stcore/health` | 외부 프론트엔드 점검 주소 |

시연용 CD는 아래 Demo 전용 Repository Variables를 사용합니다.

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| DEMO_VM_HOST | 203.0.113.10 | 시연 배포 대상 VM 주소 |
| DEMO_VM_SSH_USER | deploy | 시연 배포용 Linux 계정 |
| DEMO_VM_DEPLOY_PATH | /srv/team6/demo | 시연 Compose와 서버 환경 파일 위치 |
| DEMO_COMPOSE_PROJECT_NAME | team6-demo | 시연 Compose 프로젝트 이름 |
| DEMO_PUBLIC_HEALTHCHECK_URL | http://203.0.113.10:8501/ | 시연 프론트엔드 점검 주소 |

## GitHub Production Secrets

GitHub의 `production` Environment에 다음 Secret을 등록합니다.

| 이름 | 설명 |
| --- | --- |
| `VM_SSH_PRIVATE_KEY` | 배포용 SSH 개인키 |
| `VM_SSH_KNOWN_HOSTS` | `ssh-keyscan` 결과가 아닌 검증된 VM 호스트 키 |

애플리케이션 API 키는 GitHub에 등록하지 않습니다. 실제 `.env`는 VM의
`/srv/team6/app/.env`에서만 관리하고 CD가 덮어쓰지 않습니다.

시연용 CD는 GitHub `demo` Environment에 같은 이름의 `VM_SSH_PRIVATE_KEY`,
`VM_SSH_KNOWN_HOSTS`를 등록하거나, 별도 키를 사용합니다. 실제 애플리케이션 API 키와 Demo
계정 비밀번호는 `/srv/team6/demo/.env`에만 둡니다.

## GCP 권한

- GitHub Actions 서비스 계정: Artifact Registry Writer
- VM 서비스 계정: Artifact Registry Reader 및 Artifact Registry에 접근 가능한 VM 액세스 범위
- GitHub OIDC 주체: Workload Identity User
- 배포용 Linux 계정: Docker 실행 권한과 `/srv/team6` 쓰기 권한

## VM 최초 준비

```bash
sudo install -d -m 755 -o "$USER" -g "$USER" \
  /srv/team6/app /srv/team6/data /srv/team6/models /srv/team6/outputs

install -m 600 /dev/null /srv/team6/app/.env
nano /srv/team6/app/.env
chmod 600 /srv/team6/app/.env
```

서버 `.env`에는 실제 API 키와 다음 배포 설정을 추가합니다.

```dotenv
FRONTEND_BIND_ADDRESS=0.0.0.0
FRONTEND_PORT=8501
BACKEND_BIND_ADDRESS=127.0.0.1
BACKEND_PORT=18000
BACKEND_URL=http://backend:8000
APP_DATA_DIR=/srv/team6/data
STALE_RECOVERY_SECONDS=120
HF_TOKEN=hf_...                 # 실제 값은 이 VM의 .env에만 입력
HF_HOME=/app/.cache/huggingface
HF_HOME_HOST_PATH=/srv/team6/models
```

`HF_TOKEN`은 GitHub Secrets나 저장소 파일에 넣지 않습니다. `/srv/team6/app/.env`에만
입력하고 파일 권한은 `chmod 600 /srv/team6/app/.env`로 유지합니다. `HF_HOME_HOST_PATH`는
컨테이너 재생성 후에도 Hugging Face 가중치 캐시를 보존하는 호스트 경로입니다.

기존에 수동으로 실행한 Compose 스택이 동일 포트를 사용한다면 최초 자동 배포 전에 해당
스택만 `docker compose down`으로 종료합니다. JupyterHub 서비스는 종료하지 않습니다.

## 배포 확인

```bash
docker compose -p team6-app -f /srv/team6/app/compose.deploy.yaml ps
docker compose -p team6-app -f /srv/team6/app/compose.deploy.yaml logs --tail=200
```

배포 실패 시 Actions 로그와 위 컨테이너 로그를 먼저 확인합니다. 자동 롤백과 무중단 배포는
초기 범위에 포함하지 않습니다.
