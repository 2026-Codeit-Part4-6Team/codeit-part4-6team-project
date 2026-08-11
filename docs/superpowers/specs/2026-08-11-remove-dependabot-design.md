# Dependabot 설정 제거 설계

## 목표

프로젝트가 고정한 의존성 버전을 팀이 직접 변경하도록 유지하고, Dependabot이 자동으로 업데이트 PR을 생성하지 않게 한다.

## 변경 범위

- `.github/dependabot.yml`을 삭제한다.
- 애플리케이션 의존성, `uv.lock`, Dockerfile, CI/CD 워크플로는 변경하지 않는다.
- GitHub 저장소의 Dependabot 취약점 알림 설정은 변경하지 않는다.

## 기대 동작

- GitHub Actions와 Docker 이미지에 대한 정기 Dependabot PR이 더 이상 생성되지 않는다.
- 이 저장소 설정 파일을 근거로 하는 Dependabot 업데이트 작업이 사라진다.
- 취약점 알림의 활성화 여부는 GitHub 저장소 설정에 계속 따르며, 이 변경으로 알림을 끄지 않는다.

## 검증

- `.github/dependabot.yml`이 Git에서 삭제되었는지 확인한다.
- `pytest`, Ruff, 배포 자산 검사와 Compose smoke test가 기존대로 통과하는지 PR CI에서 확인한다.
- PR diff에 설정 파일 삭제 이외의 제품 코드 변경이 없는지 확인한다.
