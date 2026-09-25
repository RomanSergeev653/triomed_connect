# Деплой Triomed Connect на новый VPS

Прослойка принимает HTTPS от виджета amoCRM и ходит в MyDenta (FileMaker Data API).

```
amoCRM  ──HTTPS──►  Triomed Connect (этот сервер)  ──HTTPS (-k)──►  MyDenta
                    https://ВАШ_ДОМЕН
```

Let's Encrypt нужен **домен**, не голый IP. В настройках виджета этот же адрес пишется в поле **URL коннектора**.

---

## Что выбрать

| Файл | Когда |
|------|--------|
| `docker-compose.yml` | Чистый сервер, порты **80 и 443 свободны**. Nginx + certbot. |
| `docker-compose.traefik.yml` | На VPS **уже есть Traefik** (n8n и т.п.) и он занял 80/443. |

Ниже — сначала общий каркас (пользователь, DNS, клон), потом оба варианта.

Деплой с этой машины на прод **не запускается сам**: команды выполняете вы, под своим доступом.

---

## 0. Доступ по SSH (рекомендуется)

С рабочего ПК копируют только публичный ключ. Приватный ключ ноутбука на сервер не класть.

```bash
# с рабочего ПК
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@HOST
```

На сервере — отдельный пользователь **`f5-dev`**, не жить под `root`:

```bash
adduser --disabled-password --gecos "" f5-dev
mkdir -p /home/f5-dev/.ssh && chmod 700 /home/f5-dev/.ssh
cp /root/.ssh/authorized_keys /home/f5-dev/.ssh/authorized_keys
chown -R f5-dev:f5-dev /home/f5-dev/.ssh
chmod 600 /home/f5-dev/.ssh/authorized_keys
```

Дальше: `ssh f5-dev@HOST`. Репозиторий и `docker compose` — от него (нужны права docker: `usermod -aG docker f5-dev`).

Для git (Gitea) у `f5-dev` отдельная пара, не та, что для входа на VPS:

```bash
ssh-keygen -t ed25519 -C "f5-dev-gitea" -f ~/.ssh/id_ed25519_git -N ""
cat ~/.ssh/id_ed25519_git.pub
```

Публичный ключ — в Gitea (SSH keys или Deploy key). В `~/.ssh/config`:

```
Host gitea.example.com
  IdentityFile ~/.ssh/id_ed25519_git
  IdentitiesOnly yes
```

---

## 1. DNS

A-запись домена коннектора на **публичный IP этого VPS**.

```bash
dig +short connect.example.com
# должен совпасть с IP сервера
```

Пока DNS не смотрит сюда, сертификат Let's Encrypt не выпустится.

---

## 2. Код на сервере

Нужны Docker и Docker Compose v2.

```bash
sudo apt-get update
sudo apt-get install -y git docker.io docker-compose-v2
sudo usermod -aG docker f5-dev
# перелогиниться
```

```bash
cd ~
git clone git@ВАШ_GITEA:org/Triomed_connect.git triomed_connect
cd triomed_connect
cp .env.example .env
nano .env
```

---

## Вариант B — чистый сервер (nginx + certbot)

Порты 80/443 не должны быть заняты.

В `.env`:

```env
DOMAIN=connect.example.com
CERTBOT_EMAIL=admin@example.com
```

Первый выпуск сертификата:

```bash
./scripts/init-letsencrypt.sh
```

Скрипт поднимает compose, получает сертификат, перезапускает nginx.

Проверка:

```bash
curl -sS https://connect.example.com/health
# {"status":"ok"}
```

Swagger: `https://connect.example.com/docs`

Обновление:

```bash
cd ~/triomed_connect
git pull
docker compose up -d --build
```

---

## Вариант A — уже есть Traefik

**Не** поднимайте `docker-compose.yml` с nginx: 80/443 заняты Traefik.

### Узнать сеть и cert resolver

```bash
docker ps --format '{{.Names}}' | grep -i traefik
docker inspect ИМЯ_КОНТЕЙНЕРА_TRAEFIK --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}'
docker inspect ИМЯ_КОНТЕЙНЕРА_TRAEFIK --format '{{range .Config.Cmd}}{{.}}{{"\n"}}{{end}}' | grep -E 'certificatesresolvers|entrypoints'
```

Либо:

```bash
./scripts/discover-traefik.sh ИМЯ_КОНТЕЙНЕРА_TRAEFIK
```

В `.env`:

```env
DOMAIN=connect.example.com
TRAEFIK_NETWORK=имя_сети_из_inspect
TRAEFIK_CERT_RESOLVER=имя_резолвера
```

Запуск:

```bash
docker compose -f docker-compose.traefik.yml up -d --build
docker compose -f docker-compose.traefik.yml ps
docker compose -f docker-compose.traefik.yml logs -f app
```

Проверка:

```bash
curl -sS https://connect.example.com/health
# {"status":"ok"}
```

Обновление:

```bash
cd ~/triomed_connect
git pull
docker compose -f docker-compose.traefik.yml up -d --build
```

---

## 3. Виджет amoCRM

После того как `/health` отвечает `ok`:

1. Залить zip виджета **1.5.0+**.
2. В настройках виджета:
   - **URL коннектора** = `https://connect.example.com` (без слэша в конце)
   - **Адрес MyDenta** = IP:порт FileMaker, не домен коннектора
   - база, логин, пароль Data API

---

## Сеть VPS → MyDenta

С этого сервера должен открываться FileMaker:

```bash
curl -vk --connect-timeout 5 https://IP_MYDENTA:443/fmi/data/v1/productInfo
```

Если МИС в локальной сети клиники — VPN, туннель или белый IP с пробросом.

Прослойка ходит к MyDenta с `MYDENTA_VERIFY_SSL=false` (самоподписанный сертификат МИС).

---

## Troubleshooting

### 404 от Traefik

- Контейнер запущен: `docker ps | grep triomed`
- Labels: `docker inspect triomed-connect --format '{{json .Config.Labels}}'`
- Контейнер в той же сети, что Traefik

### 502 Bad Gateway

- Логи: `docker compose -f docker-compose.traefik.yml logs app` (или `docker compose logs app`)
- Из сети Traefik: `docker run --rm --network ИМЯ_СЕТИ curlimages/curl http://triomed-connect:8000/health`

### SSL / ERR_CERT_COMMON_NAME_INVALID

- Заходите по **домену** из `DOMAIN`, не по IP.
- A-запись домена указывает на **этот** VPS, не на старый сервер.
- Порт 80 снаружи нужен для ACME.

### 502 «MyDenta authorization failed»

Коннектор жив, но не достучался до МИС: host/database/credentials и сеть до FileMaker.

---

## Полезные команды

```bash
# standalone
docker compose logs -f app
docker compose restart app
docker compose down

# Traefik
docker compose -f docker-compose.traefik.yml logs -f app
docker compose -f docker-compose.traefik.yml restart app
docker compose -f docker-compose.traefik.yml down
```
