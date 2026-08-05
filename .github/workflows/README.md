# CI/CD 운영 안내

현재 워크플로는 서비스 요구사항과 독립적인 컨테이너 검증 및 배포 경로만 제공합니다.

## CI

`ci.yml`은 Pull Request, `main` Push, 수동 실행 시 다음 작업을 수행합니다.

1. `uv.lock` 기반 의존성 설치
2. Ruff 검사 및 Pytest 실행
3. `requirements.txt` 동기화 확인
4. Docker Compose 설정 및 이미지 빌드 확인

## CD

`deploy.yml`은 초기 오작동을 방지하기 위해 수동 실행만 허용합니다. 다음 순서로 동작합니다.

1. GitHub OIDC와 Google Cloud Workload Identity Federation으로 인증
2. 프론트엔드와 백엔드 이미지를 Artifact Registry에 커밋 SHA 태그로 업로드
3. 배포용 Compose 파일과 스크립트를 VM으로 전송
4. VM에서 이미지를 Pull하고 컨테이너를 교체
5. 두 서비스의 Docker 헬스체크 확인

수동 배포가 안정적으로 동작한 이후 `deploy.yml`에 `main` Push 트리거를 추가합니다.

## GitHub Actions Variables

저장소 `Settings > Secrets and variables > Actions > Variables`에 등록합니다.

| 이름 | 예시 | 설명 |
| --- | --- | --- |
| `GCP_PROJECT_ID` | `sprint-ai-chunk3-02` | GCP 프로젝트 ID |
| `GCP_REGION` | `us-central1` | Artifact Registry 리전 |
| `ARTIFACT_REGISTRY_REPOSITORY` | `codeit-part4-6team` | Docker 저장소 이름 |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/.../providers/...` | GitHub OIDC Provider 전체 경로 |
| `GCP_SERVICE_ACCOUNT` | `github-actions@...iam.gserviceaccount.com` | 이미지 업로드용 서비스 계정 |
| `VM_HOST` | `34.60.89.231` | 배포 대상 VM 주소 |
| `VM_SSH_USER` | `deploy` | 배포 전용 리눅스 계정 |
| `VM_DEPLOY_PATH` | `/home/deploy/codeit-part4-6team-project` | 배포 파일 저장 경로 |

## production Environment Secrets

저장소 `Settings > Environments > production`에 등록합니다. 가능하면 Required reviewers에 배포 승인자를 지정합니다.

| 이름 | 설명 |
| --- | --- |
| `VM_SSH_PRIVATE_KEY` | 배포 전용 SSH 개인키 원문 |
| `VM_SSH_KNOWN_HOSTS` | `ssh-keyscan -H VM주소` 결과 |

개인 SSH 키나 평소 사용하는 비밀번호를 배포에 재사용하지 않습니다.

## GCP 및 VM 사전 조건

- GitHub Actions 서비스 계정: Artifact Registry Writer 권한
- Workload Identity Provider: 이 저장소의 Workflow만 서비스 계정을 사용할 수 있도록 제한
- VM 서비스 계정: Artifact Registry Reader 권한
- VM 배포 계정: Docker 명령 실행 권한
- VM 배포 경로: 배포 계정이 쓰기 가능한 디렉터리
- VM `.env`: 서버에만 저장하며 `FRONTEND_PORT=80` 등 운영값을 지정

현재 배포 스크립트는 VM의 `gcloud`가 VM 서비스 계정으로 Artifact Registry 접근 토큰을 발급받을 수 있다고 가정합니다.
