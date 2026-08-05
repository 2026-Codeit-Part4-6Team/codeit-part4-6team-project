#!/usr/bin/env bash

set -Eeuo pipefail

if [[ $# -ne 3 ]]; then
  echo "사용법: $0 <이미지 경로> <이미지 태그> <Registry 호스트>" >&2
  exit 2
fi

image_base="$1"
image_tag="$2"
registry_host="$3"
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

for command in docker gcloud; do
  if ! command -v "${command}" >/dev/null 2>&1; then
    echo "필수 명령을 찾을 수 없습니다: ${command}" >&2
    exit 1
  fi
done

if [[ ! -f "${project_dir}/.env" ]]; then
  cp "${project_dir}/.env.example" "${project_dir}/.env"
  echo "${project_dir}/.env를 기본값으로 생성했습니다. 운영 포트를 확인해주세요."
fi

gcloud auth print-access-token \
  | docker login -u oauth2accesstoken --password-stdin "${registry_host}"

export IMAGE_BASE="${image_base}"
export IMAGE_TAG="${image_tag}"

compose=(
  docker compose
  --env-file "${project_dir}/.env"
  -f "${project_dir}/compose.deploy.yaml"
)

"${compose[@]}" pull
"${compose[@]}" up -d --remove-orphans

wait_for_healthy() {
  local service="$1"
  local container_id
  local status

  for _ in {1..30}; do
    container_id="$("${compose[@]}" ps -a -q "${service}")"
    if [[ -n "${container_id}" ]]; then
      status="$(docker inspect \
        --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' \
        "${container_id}")"
      if [[ "${status}" == "healthy" ]]; then
        return 0
      fi
      if [[ "${status}" == "exited" || "${status}" == "unhealthy" ]]; then
        break
      fi
    fi
    sleep 2
  done

  echo "${service} 서비스가 정상 상태가 되지 않았습니다." >&2
  "${compose[@]}" logs --tail=100 "${service}" >&2 || true
  return 1
}

wait_for_healthy backend
wait_for_healthy frontend

"${compose[@]}" ps
docker logout "${registry_host}" >/dev/null 2>&1 || true

echo "배포 완료: backend/frontend 이미지 태그 ${image_tag}"
