#!/usr/bin/env bash

set -Eeuo pipefail

: "${IMAGE_BASE:?IMAGE_BASE is required}"
: "${IMAGE_TAG:?IMAGE_TAG is required}"

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-team6-app}"
COMPOSE_FILE="${COMPOSE_FILE:-compose.deploy.yaml}"
REGISTRY_HOST="${IMAGE_BASE%%/*}"

if [[ ! -f .env ]]; then
  echo "배포 경로에 .env 파일이 없습니다: $(pwd)/.env" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker가 설치되어 있지 않습니다." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose 플러그인을 사용할 수 없습니다." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "배포 설정과 VM 서비스 계정 토큰을 처리하려면 python3가 필요합니다." >&2
  exit 1
fi

export IMAGE_BASE IMAGE_TAG COMPOSE_PROJECT_NAME
compose=(docker compose -p "$COMPOSE_PROJECT_NAME" --env-file .env -f "$COMPOSE_FILE")

app_data_dir="$("${compose[@]}" config --format json | python3 -c '
import json
import sys

config = json.load(sys.stdin)
volumes = config["services"]["backend"].get("volumes", [])
matches = [
    volume["source"]
    for volume in volumes
    if volume.get("type") == "bind" and volume.get("target") == "/app/data"
]
if len(matches) != 1:
    raise SystemExit("backend의 /app/data 바인드 마운트를 하나만 설정해야 합니다.")
print(matches[0])
')"

if ! mkdir -p "$app_data_dir"; then
  echo "데이터 디렉터리를 만들 수 없습니다: $app_data_dir" >&2
  exit 1
fi

if [[ ! -w "$app_data_dir" ]]; then
  echo "데이터 디렉터리에 쓰기 권한이 없습니다: $app_data_dir" >&2
  exit 1
fi

access_token="$(python3 - <<'PY'
import json
import urllib.request

request = urllib.request.Request(
    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
    headers={"Metadata-Flavor": "Google"},
)
with urllib.request.urlopen(request, timeout=10) as response:
    print(json.load(response)["access_token"])
PY
)"

printf '%s\n' "$access_token" \
  | docker login -u oauth2accesstoken --password-stdin "https://${REGISTRY_HOST}"
unset access_token

"${compose[@]}" pull

if ! "${compose[@]}" up -d --remove-orphans --wait --wait-timeout 180; then
  "${compose[@]}" ps >&2 || true
  "${compose[@]}" logs --no-color --tail=200 >&2 || true
  exit 1
fi

if ! "${compose[@]}" exec -T frontend node - < scripts/smoke_frontend_backend.js
then
  "${compose[@]}" ps >&2 || true
  "${compose[@]}" logs --no-color --tail=200 >&2 || true
  exit 1
fi

"${compose[@]}" ps
