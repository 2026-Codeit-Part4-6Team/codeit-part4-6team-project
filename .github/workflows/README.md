# CI/CD 운영 안내

## 현재 범위

- CI는 Python 테스트와 Docker Compose 기반 서비스 기동을 검증합니다.
- CD는 백엔드와 프론트엔드 이미지만 Artifact Registry에 저장하고 GCP VM에 배포합니다.
- JupyterHub, 모델 실험 환경, Triton, 모델 가중치는 현재 배포 대상이 아닙니다.
- 배포 이미지는 `latest`가 아니라 Git 커밋 SHA로 식별합니다.

## 워크플로 트리거

`ci.yml`은 Main 대상 PR과 Main Push에서 실행합니다.

`deploy.yml`은 최초 배포 검증을 위해 현재 `chore/ci-cd-pipeline` Push에서 실행합니다.
배포가 정상 동작하면 해당 브랜치 조건을 `main`으로 변경한 뒤 Main에 머지합니다.

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

## GitHub Production Secrets

GitHub의 `production` Environment에 다음 Secret을 등록합니다.

| 이름 | 설명 |
| --- | --- |
| `VM_SSH_PRIVATE_KEY` | 배포용 SSH 개인키 |
| `VM_SSH_KNOWN_HOSTS` | `ssh-keyscan` 결과가 아닌 검증된 VM 호스트 키 |

애플리케이션 API 키는 GitHub에 등록하지 않습니다. 실제 `.env`는 VM의
`/srv/team6/app/.env`에서만 관리하고 CD가 덮어쓰지 않습니다.

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
```

기존에 수동으로 실행한 Compose 스택이 동일 포트를 사용한다면 최초 자동 배포 전에 해당
스택만 `docker compose down`으로 종료합니다. JupyterHub 서비스는 종료하지 않습니다.

## 배포 확인

```bash
docker compose -p team6-app -f /srv/team6/app/compose.deploy.yaml ps
docker compose -p team6-app -f /srv/team6/app/compose.deploy.yaml logs --tail=200
```

배포 실패 시 Actions 로그와 위 컨테이너 로그를 먼저 확인합니다. 자동 롤백과 무중단 배포는
초기 범위에 포함하지 않습니다.
