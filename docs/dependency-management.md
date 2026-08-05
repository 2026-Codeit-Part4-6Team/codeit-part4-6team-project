# Python 의존성 관리

이 프로젝트는 Python 3.11과 uv를 기준으로 의존성을 관리합니다.

## 관리 파일

| 파일 | 역할 | 수정 방법 |
| --- | --- | --- |
| `pyproject.toml` | 직접 의존성과 도구 설정 | `uv add`, `uv remove` 사용 |
| `uv.lock` | 전체 의존성 버전 잠금 | uv가 자동 생성 |
| `requirements.txt` | uv를 사용할 수 없는 환경의 호환용 파일 | `uv export`로 생성 |
| `.python-version` | 로컬 Python 기준 버전 | Python 버전 변경 시 팀 합의 |

`uv.lock`과 `requirements.txt`는 직접 수정하지 않습니다. `pip install`로만 추가한 패키지는 다른 환경에서 재현되지 않으므로 프로젝트 의존성으로 인정하지 않습니다.

## 의존성 그룹

| 그룹 | 용도 |
| --- | --- |
| `backend` | FastAPI 백엔드 실행 의존성 |
| `frontend` | Streamlit 프론트엔드 실행 의존성 |
| `dev` | 테스트와 정적 검사 도구 |

모델, Triton, Notebook 관련 패키지는 담당 범위와 실행환경이 확정된 뒤 별도 그룹으로 추가합니다.

## 개발환경 구성

저장소 루트에서 실행합니다.

```bash
uv sync --locked --group backend --group frontend --group dev
```

`--locked`는 `uv.lock`을 변경하지 않고 기록된 버전 그대로 설치합니다. 의존성을 변경하려는 경우에만 아래 명령을 사용합니다.

```bash
# 의존성 추가
uv add --group backend 패키지명
uv add --group frontend 패키지명
uv add --group dev 패키지명

# 의존성 제거
uv remove --group backend 패키지명
uv remove --group frontend 패키지명
uv remove --group dev 패키지명
```

## requirements.txt 갱신

의존성을 변경했다면 호환용 파일을 다시 생성합니다.

```bash
uv export --locked --no-default-groups \
  --group backend --group frontend \
  --format requirements.txt --output-file requirements.txt
```

## Docker

Docker 이미지는 같은 `uv.lock`을 사용하되 서비스에 필요한 그룹만 설치합니다.

```text
backend image  = Python 3.11 + backend group
frontend image = Python 3.11 + frontend group
```

Dockerfile의 uv 버전은 재현성을 위해 고정합니다. 버전을 변경할 때는 백엔드와 프론트엔드 Dockerfile을 함께 수정하고 두 이미지를 모두 빌드합니다.

## 의존성 변경 PR 확인사항

- `pyproject.toml`과 `uv.lock`을 함께 반영했는가
- `requirements.txt`를 다시 생성했는가
- 의존성을 올바른 그룹에 추가했는가
- `uv sync --locked`가 성공하는가
- 백엔드와 프론트엔드 이미지가 모두 빌드되는가

JupyterHub의 관리 환경은 프로젝트 환경과 분리합니다. 공용 실험 커널 정책이 확정되기 전까지 TLJH 관리용 Python 환경에 프로젝트 패키지를 직접 설치하지 않습니다.
