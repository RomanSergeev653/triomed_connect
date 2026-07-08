#!/bin/bash
# Показывает параметры Traefik для настройки docker-compose.traefik.yml
set -euo pipefail

CONTAINER="${1:-n8n-compose-file-traefik-1}"

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  echo "Контейнер '$CONTAINER' не найден."
  echo "Запущенные контейнеры:"
  docker ps --format '  {{.Names}}'
  exit 1
fi

echo "=== Traefik container: $CONTAINER ==="
echo

echo "Docker networks:"
docker inspect "$CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}  {{$k}}{{"\n"}}{{end}}'

echo "Entrypoints:"
docker inspect "$CONTAINER" --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}' \
  | grep -E 'entrypoints\.' || true

echo
echo "Cert resolvers:"
docker inspect "$CONTAINER" --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}' \
  | grep -E 'certificatesresolvers\.' || true

echo
echo "=== Скопируйте в .env ==="
NETWORK=$(docker inspect "$CONTAINER" --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
RESOLVER=$(docker inspect "$CONTAINER" --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}' \
  | grep -oP 'certificatesresolvers\.\K[^.]+' | head -1)

cat <<EOF
DOMAIN=mydenta.limbrs.top
TRAEFIK_NETWORK=${NETWORK:-ЗАПОЛНИТЕ_ВРУЧНУЮ}
TRAEFIK_CERT_RESOLVER=${RESOLVER:-ЗАПОЛНИТЕ_ВРУЧНУЮ}
EOF
