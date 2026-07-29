# Triomed Connect

HTTPS-прослойка между **amoCRM** и МИС **MyDenta** (FileMaker Data API).

amoCRM не может ходить на MyDenta напрямую: у сервера MyDenta недоверенный SSL-сертификат. Прослойка принимает запросы по нормальному HTTPS и сама обращается к MyDenta с `verify=False` (аналог `curl -k`).

```
amoCRM  ──HTTPS──►  Triomed Connect  ──HTTPS (-k)──►  MyDenta
                       mydenta.limbrs.top              host:443
```

## Возможности

- REST API с JSON-телом для amoCRM
- CORS для виджетов с доменов `*.amocrm.ru` / `*.kommo.com` (иначе браузер блокирует preflight)
- Авторизация в MyDenta и кэш сессии (~14 мин)
- Поиск свободных слотов, записей пациента, создание и перезапись
- Деплой через Docker + Traefik (или standalone nginx + Let's Encrypt)

## Быстрый старт (локально)

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health  
- Swagger: http://localhost:8000/docs  

## API

Базовый URL (прод): `https://mydenta.limbrs.top`

Во всех рабочих запросах передаются учётные данные MyDenta:

| Поле | Описание |
|------|----------|
| `host` | Адрес MyDenta, например `178.124.210.218:443` |
| `database` | Имя базы FileMaker, например `My_Dent` |
| `username` / `password` | Учётная запись Data API |

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/health` | Проверка работы |
| POST | `/api/v1/free-slots` | Свободные слоты |
| POST | `/api/v1/appointments/search` | Записи пациента |
| POST | `/api/v1/appointments` | Новая запись |
| POST | `/api/v1/appointments/reschedule` | Перезапись |
| POST | `/api/v1/sessions/logout` | Закрыть сессию MyDenta (опционально) |

### Примеры

**Свободные слоты**

```bash
curl -s -X POST https://mydenta.limbrs.top/api/v1/free-slots \
  -H "Content-Type: application/json" \
  -d '{
    "host": "178.124.210.218:443",
    "database": "My_Dent",
    "username": "Api_Test",
    "password": "ApiTest",
    "date_start": "01.07.2026",
    "date_end": "07.07.2026",
    "doctor_ids": ["25"]
  }'
```

**Поиск записей**

```bash
curl -s -X POST https://mydenta.limbrs.top/api/v1/appointments/search \
  -H "Content-Type: application/json" \
  -d '{
    "host": "178.124.210.218:443",
    "database": "My_Dent",
    "username": "Api_Test",
    "password": "ApiTest",
    "phone": "375291234567",
    "last_name": "Иванов",
    "first_name": "Иван",
    "middle_name": "Иванович"
  }'
```

**Новая запись**

```bash
curl -s -X POST https://mydenta.limbrs.top/api/v1/appointments \
  -H "Content-Type: application/json" \
  -d '{
    "host": "178.124.210.218:443",
    "database": "My_Dent",
    "username": "Api_Test",
    "password": "ApiTest",
    "phone_local": "291234567",
    "phone_code": "375",
    "last_name": "Иванов",
    "first_name": "Иван",
    "middle_name": "Иванович",
    "date": "01.07.2026",
    "start_time": "08:00:00",
    "end_time": "09:00:00",
    "doctor_id": "25"
  }'
```

Интерактивная документация: `/docs`.

### Сессия MyDenta

amoCRM **не управляет** логином/логаутом. Прослойка сама:

1. логинится в MyDenta при необходимости;
2. кэширует токен ~14 минут;
3. при `401` переавторизуется.

Логаут (`/api/v1/sessions/logout`) нужен только если сессию нужно закрыть принудительно.

## Деплой

### Вариант A — Traefik (рекомендуется)

Если на VPS уже есть Traefik (n8n и др.), используйте:

```bash
cp .env.example .env
# DOMAIN=mydenta.limbrs.top
# TRAEFIK_NETWORK=...
# TRAEFIK_CERT_RESOLVER=...

./scripts/discover-traefik.sh n8n-compose-file-traefik-1   # подскажет значения
docker compose -f docker-compose.traefik.yml up -d --build
```

Подробно: [docs/DEPLOY.md](docs/DEPLOY.md).

### Вариант B — standalone (nginx + certbot)

Только если порты 80/443 свободны:

```bash
cp .env.example .env
# DOMAIN=...
# CERTBOT_EMAIL=...

./scripts/init-letsencrypt.sh
```

### Обновление

```bash
cd ~/workprojects/triomed_connect
git pull
docker compose -f docker-compose.traefik.yml up -d --build
```

## Структура проекта

```
app/                      FastAPI-приложение
  main.py
  routers/api.py          REST-эндпоинты
  mydenta_client.py       Клиент FileMaker Data API
  schemas.py              JSON-модели
  parsers.py              Разбор scriptResult
  token_cache.py          Кэш сессии
docker/                   nginx (standalone)
scripts/                  Traefik discover, Let's Encrypt
docker-compose.traefik.yml
docker-compose.yml
docs/                     Документация MyDenta и деплой
```

## Коды ошибок MyDenta (script)

| Код | Смысл |
|-----|--------|
| 0 | OK |
| 100 | Неверные / не указаны даты поиска |
| 200 | Нет расписания на дату |
| 400 | Нет записей |
| 500 | Не хватает параметров записи/перезаписи |
| 600 | Нет записей пациента |
| 700 | Нет обязательных параметров поиска |
| 800 | Отказ по правилам сопоставления ФИО/телефона |

FileMaker Data API:

| Код | Смысл |
|-----|--------|
| 104 | Скрипт не найден на layout (`script is missing`) |

HTTP-ответы прослойки:

| HTTP | Когда |
|------|--------|
| 200 | Успех |
| 422 | Невалидный JSON / поля |
| 502 | MyDenta ответила ошибкой или недоступна |
| 504 | Timeout при обращении к MyDenta |

## Требования к MyDenta

В базе должны быть опубликованы скрипты на layout `time_free`:

- `find_free_time`
- `find_record_shedule`
- `create_record_shedule_api`

У пользователя API — доступ к Data API и этим скриптам.

Прослойка ходит к MyDenta по **HTTPS** без проверки сертификата (`MYDENTA_VERIFY_SSL=false` по умолчанию), HTTP/1.1.

## Переменные окружения

См. [.env.example](.env.example).

| Переменная | Описание |
|------------|----------|
| `DOMAIN` | Домен прослойки |
| `TRAEFIK_NETWORK` | Docker-сеть Traefik |
| `TRAEFIK_CERT_RESOLVER` | ACME resolver Traefik |
| `TOKEN_TTL_SECONDS` | TTL кэша токена (по умолчанию 840) |
| `MYDENTA_REQUEST_TIMEOUT` | Timeout к MyDenta, сек (по умолчанию 30) |
| `MYDENTA_VERIFY_SSL` | Проверять SSL MyDenta (по умолчанию `false`) |

## Логи

```bash
docker compose -f docker-compose.traefik.yml logs -f app
# или
docker logs -f triomed-connect
```

## Документация

- [docs/DEPLOY.md](docs/DEPLOY.md) — деплой с Traefik
- [docs/Варианты запросов (2).txt](docs/Варианты%20запросов%20(2).txt) — описание API MyDenta
- [docs/MyDenta.postman_collection.json](docs/MyDenta.postman_collection.json) — Postman-коллекция
