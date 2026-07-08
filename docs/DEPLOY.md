# Деплой Triomed Connect на VPS с Traefik

Инструкция для сервера, где **уже работает Traefik** (как у вас: `n8n-compose-file-traefik-1` на портах 80/443).

> **Не используйте** `docker-compose.yml` с nginx+certbot на этом сервере — порты 80/443 уже заняты Traefik.  
> Используйте **`docker-compose.traefik.yml`**.

---

## Как это работает вместе с другими сайтами

Traefik — единая «входная дверь» на сервер. Он смотрит на **Host** в запросе и направляет трафик в нужный контейнер:

```
Интернет
   │
   ▼
Traefik (:80 / :443)  ← один SSL, один acme.json (~/letsencrypt/acme.json)
   │
   ├── n8n.limbrs.top      → контейнер n8n
   ├── mydenta.limbrs.top  → контейнер triomed-connect  ← новый сервис
   ├── vaultwarden...      → другой контейнер
   └── ...
```

Сервисы **не конфликтуют**: у каждого свой домен/поддомен и свои Traefik labels. SSL для `mydenta.limbrs.top` Traefik получит автоматически через уже настроенный ACME.

---

## Шаг 0. Подготовка DNS

В панели DNS для `limbrs.top` добавьте A-запись:

| Тип | Имя    | Значение        |
|-----|--------|-----------------|
| A   | mydenta | IP вашего VPS |

Проверка (с любого ПК):

```bash
dig +short mydenta.limbrs.top
# должен вернуть IP сервера
```

Подождите 5–30 минут, пока DNS обновится.

---

## Шаг 1. Узнать параметры Traefik на сервере

Подключитесь к VPS:

```bash
ssh root@Limb3
```

### 1.1. Имя Docker-сети Traefik

```bash
docker inspect n8n-compose-file-traefik-1 --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
```

Запишите имя сети (часто что-то вроде `n8n-compose-file_default` или `traefik`).

Посмотреть все сети:

```bash
docker network ls
```

### 1.2. Имя cert resolver (Let's Encrypt)

```bash
docker inspect n8n-compose-file-traefik-1 --format '{{json .Config.Cmd}}' | tr ',' '\n' | grep certificat
```

Ищите строку вида:

```
--certificatesresolvers.ИМЯ_РЕЗОЛВЕРА.acme...
```

**ИМЯ_РЕЗОЛВЕРА** — это значение для `TRAEFIK_CERT_RESOLVER` (часто `mytlschallenge`, `letsencrypt`, `le`).

Пример полной команды Traefik:

```bash
docker inspect n8n-compose-file-traefik-1 --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}'
```

### 1.3. Entrypoints

Обычно уже настроены:

- `web` — порт 80 (редирект на HTTPS)
- `websecure` — порт 443

Проверка:

```bash
docker inspect n8n-compose-file-traefik-1 --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}' | grep entrypoints
```

---

## Шаг 2. Загрузить проект на сервер

```bash
cd ~/workprojects   # или другая папка для проектов
git clone <URL_репозитория> triomed_connect
cd triomed_connect
```

Если репозитория ещё нет — скопируйте файлы через `scp` / `rsync` в `~/workprojects/triomed_connect`.

---

## Шаг 3. Настроить `.env`

```bash
cp .env.example .env
nano .env
```

Минимум для Traefik-деплоя:

```env
DOMAIN=mydenta.limbrs.top
TRAEFIK_NETWORK=n8n-compose-file_default
TRAEFIK_CERT_RESOLVER=mytlschallenge
```

`TRAEFIK_NETWORK` и `TRAEFIK_CERT_RESOLVER` — из шага 1.

---

## Шаг 4. Запуск

```bash
docker compose -f docker-compose.traefik.yml up -d --build
```

Проверка контейнера:

```bash
docker compose -f docker-compose.traefik.yml ps
docker compose -f docker-compose.traefik.yml logs -f app
```

---

## Шаг 5. Проверка

### Healthcheck

```bash
curl -s https://mydenta.limbrs.top/health
# {"status":"ok"}
```

### Swagger (документация API)

Откройте в браузере: **https://mydenta.limbrs.top/docs**

### Тестовый запрос к MyDenta (когда знаете host базы)

```bash
curl -s -X POST https://mydenta.limbrs.top/api/v1/free-slots \
  -H "Content-Type: application/json" \
  -d '{
    "host": "IP_ИЛИ_ХОСТ_MYDENTA:ПОРТ",
    "database": "ИМЯ_БАЗЫ",
    "username": "Api_Test",
    "password": "ApiTest",
    "date_start": "01.07.2026",
    "date_end": "07.07.2026"
  }'
```

---

## Шаг 6. Обновление после изменений в коде

```bash
cd ~/workprojects/triomed_connect
git pull
docker compose -f docker-compose.traefik.yml up -d --build
```

---

## Важно: доступ VPS → MyDenta

Прослойка на VPS ходит в MyDenta по **HTTP** (`http://host:port/...`).

Убедитесь, что с VPS до сервера MyDenta есть сетевой доступ:

```bash
curl -v --connect-timeout 5 http://IP_MYDENTA:ПОРТ/fmi/data/v1/databases/ИМЯ_БАЗЫ/sessions
```

Если MyDenta в локальной сети клиники — нужен VPN, туннель или белый IP с пробросом порта.

---

## Добавление других сервисов (общая схема)

Для любого нового сайта на том же VPS:

1. DNS: A-запись на IP VPS.
2. Docker-контейнер **без** проброса 80/443 наружу.
3. Подключить контейнер к **той же Docker-сети**, что и Traefik.
4. Traefik labels:
   - `traefik.enable=true`
   - `traefik.http.routers.<имя>.rule=Host(\`domain.example\`)`
   - `traefik.http.routers.<имя>.entrypoints=websecure`
   - `traefik.http.routers.<имя>.tls.certresolver=<ваш_resolver>`
   - `traefik.http.services.<имя>.loadbalancer.server.port=<порт_приложения>`

Traefik сам выпустит/обновит сертификат для нового домена.

---

## Troubleshooting

### 404 от Traefik

- Контейнер `triomed-connect` запущен? `docker ps | grep triomed`
- Labels верные? `docker inspect triomed-connect --format '{{json .Config.Labels}}'`
- Контейнер в той же сети, что Traefik?

```bash
docker network inspect n8n-compose-file_default | grep triomed
```

### 502 Bad Gateway

- Приложение слушает 8000: `docker compose -f docker-compose.traefik.yml logs app`
- Проверка изнутри сети Traefik:

```bash
docker run --rm --network n8n-compose-file_default curlimages/curl \
  http://triomed-connect:8000/health
```

### SSL не выдаётся

- DNS `mydenta.limbrs.top` указывает на VPS?
- Порт 80 доступен снаружи (нужен для ACME challenge)?
- Логи Traefik: `docker logs n8n-compose-file-traefik-1 --tail 50`

### Ошибка 502 с текстом «MyDenta authorization failed»

Прослойка работает, но не достучалась до MyDenta — проверьте host/database/credentials и сеть до MyDenta.

---

## Полезные команды

```bash
# Логи приложения
docker compose -f docker-compose.traefik.yml logs -f app

# Перезапуск
docker compose -f docker-compose.traefik.yml restart app

# Остановка
docker compose -f docker-compose.traefik.yml down

# Автоподсказка по Traefik (на сервере)
./scripts/discover-traefik.sh n8n-compose-file-traefik-1
```

---

## Два варианта деплоя в проекте

| Файл | Когда использовать |
|------|-------------------|
| `docker-compose.traefik.yml` | VPS с Traefik (**ваш случай**) |
| `docker-compose.yml` | Чистый сервер без Traefik (nginx + certbot) |
