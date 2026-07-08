#!/bin/bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "Создайте .env из .env.example и укажите DOMAIN, CERTBOT_EMAIL"
  exit 1
fi

set -a
source .env
set +a

if [ -z "${DOMAIN:-}" ] || [ -z "${CERTBOT_EMAIL:-}" ]; then
  echo "В .env должны быть заданы DOMAIN и CERTBOT_EMAIL"
  exit 1
fi

echo "Запуск сервисов (HTTP)..."
docker compose up -d --build

echo "Получение сертификата Let's Encrypt для ${DOMAIN}..."
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email "${CERTBOT_EMAIL}" \
  --agree-tos \
  --no-eff-email \
  -d "${DOMAIN}"

echo "Перезапуск nginx для включения HTTPS..."
docker compose restart nginx

echo "Готово. API доступен по https://${DOMAIN}"
