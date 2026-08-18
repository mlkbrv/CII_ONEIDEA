# CCI Cola Fest — что делать сейчас и как всё задеплоить

Этот файл — рабочая инструкция. Backend, Mini App и бот уже написаны. Тебе нужно создать Telegram-бота, выдать ему HTTPS-ссылку на Mini App и запустить сервер.

## Что уже есть в проекте

- FastAPI API: `POST /api/v1/auth/telegram`, `POST /api/v1/promo-codes/redeem`
- Mini App: экран ввода/скана промокода в `miniapp/` (открывается как `/miniapp/`)
- Telegram-бот: `/start` открывает Mini App, `/redeem КОД` активирует код из чата
- PostgreSQL-модели, Alembic-миграция, скрипт генерации кодов

Бот стартует вместе с API (polling), если в `.env` задан `TELEGRAM_BOT_TOKEN`.

---

## Шаг 0. Что подготовить

На компьютере:

- Python 3.12
- PostgreSQL 18 (у тебя уже ставился) **или** Docker Desktop
- ngrok (для локального теста Telegram) — https://ngrok.com/download
- токен бота от @BotFather

Telegram Mini App **не работает по http://localhost**. Нужен HTTPS. Для локалки это ngrok, для боя — домен.

---

## Шаг 1. Создать бота в Telegram

1. Открой [@BotFather](https://t.me/BotFather)
2. `/newbot`
3. Имя, например `CCI Cola Fest`
4. Username, например `cci_cola_fest_bot`
5. Скопируй токен вида `123456:ABC...` — это `TELEGRAM_BOT_TOKEN`

Команды бота:

```
/setcommands
```

Отправь BotFather:

```
start - Открыть Cola Fest
redeem - Активировать промокод
```

Пока **не** ставь Mini App URL: сначала подними сервер и получи HTTPS-адрес.

---

## Шаг 2. Локальный запуск (Windows)

В PowerShell из папки проекта `C:\Users\ASUS\Downloads\OneIdea`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 2.1. База

Если PostgreSQL уже запущен (как раньше), база `cci` и пользователь `cci` / пароль `postgres` уже есть.

Если нет — через Docker:

```powershell
docker compose up postgres -d
```

Миграции:

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

### 2.2. Файл `.env`

Скопируй `.env.example` в `.env` и заполни:

```env
DATABASE_URL=postgresql+asyncpg://cci:postgres@127.0.0.1:5432/cci
TELEGRAM_BOT_TOKEN=123456:ABC_твой_токен
TELEGRAM_WEBAPP_URL=
JWT_SECRET=придумай-длинный-секрет-минимум-32-символа
PROMO_CODE_PEPPER=
BOT_POLLING=true
```

`TELEGRAM_WEBAPP_URL` пока оставь пустым — впишешь после ngrok.

### 2.3. API + Mini App + бот

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Проверка в браузере:

- http://127.0.0.1:8000/health → `{"status":"ok"}`
- http://127.0.0.1:8000/docs → Swagger
- http://127.0.0.1:8000/miniapp/ → экран промокода (из обычного браузера redeem не сработает, нужен Telegram)

Не используй `--reload`, пока включён бот: reload поднимает два polling-процесса.

---

## Шаг 3. HTTPS через ngrok (обязательно для Telegram)

В **новом** окне PowerShell:

```powershell
ngrok http 8000
```

Скопируй URL вида `https://abc123.ngrok-free.app`.

В `.env`:

```env
TELEGRAM_WEBAPP_URL=https://abc123.ngrok-free.app/miniapp/
```

Перезапусти uvicorn.

### 3.1. Привязать Mini App в BotFather

1. @BotFather → `/newapp` (или `/mybots` → твой бот → Bot Settings → Menu Button / Configure Mini App)
2. Выбери бота
3. Title: `CCI`
4. Web App URL: `https://abc123.ngrok-free.app/miniapp/`
5. `/setmenubutton` → URL тот же, текст `CCI`

Каждый раз, когда ngrok перезапускается, URL меняется. Тогда обнови `.env` и BotFather.

---

## Шаг 4. Сгенерировать промокоды

Пока uvicorn работает, в другом окне:

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe scripts\generate_promo_codes.py --count 1000 --coin-reward 50 --output promo_codes.csv
```

С опциональной датой конца фестиваля:

```powershell
.\.venv\Scripts\python.exe scripts\generate_promo_codes.py --count 1000 --coin-reward 50 --expires-at 2026-09-30T23:59:59+00:00 --output promo_codes.csv
```

- В БД сохраняются только SHA-256 хеши
- `promo_codes.csv` — plaintext для печати наклеек. **Не коммить и не светить**

---

## Шаг 5. Как проверить

1. Найди бота в Telegram, нажми **Start**
2. Должна быть кнопка **Открыть приложение**
3. В Mini App введи код из CSV → должно начислить монеты
4. Тот же код второй раз → «уже использован»
5. В чате с ботом: `/redeem КОД`

Если Mini App пишет «Открой из Telegram» — открыл HTML в браузере, а не через бота.

Если 503 — в `.env` пустой `TELEGRAM_BOT_TOKEN`, либо uvicorn запущен без `.env`.

Если кнопка Mini App не открывается — URL не HTTPS или не тот ngrok-хост.

---

## Шаг 6. Боевой деплой (VPS + Docker)

Нужен сервер с Docker и домен (или IP + Cloudflare) с HTTPS.

Пример на Ubuntu:

```bash
sudo apt update
sudo apt install docker.io docker-compose-v2 nginx certbot python3-certbot-nginx
```

Скопируй проект на сервер, в корне создай `.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBAPP_URL=https://твой-домен/miniapp/
JWT_SECRET=очень-длинный-случайный-секрет
PROMO_CODE_PEPPER=случайная-строка
```

Запуск:

```bash
docker compose up -d --build
```

Compose поднимает PostgreSQL и API (внутри него бот polling + Mini App + миграции).

Nginx (файл `/etc/nginx/sites-available/cci`):

```nginx
server {
    listen 80;
    server_name твой-домен;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/cci /etc/nginx/sites-enabled/cci
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d твой-домен
```

Проверка: `https://твой-домен/health`

Потом в BotFather поставь постоянный URL:

```
https://твой-домен/miniapp/
```

И в `.env` тот же `TELEGRAM_WEBAPP_URL`. Перезапуск:

```bash
docker compose up -d
```

Генерация кодов на сервере:

```bash
docker compose exec api python scripts/generate_promo_codes.py --count 1000 --coin-reward 50 --output /tmp/promo_codes.csv
docker compose cp api:/tmp/promo_codes.csv ./promo_codes.csv
```

---

## Альтернатива без своего VPS

Подойдёт любой хост с Docker/HTTPS: Railway, Render, Fly.io, Timeweb Cloud.

Нужно:

1. PostgreSQL addon
2. Сервис из этого репозитория, команда как в Dockerfile
3. Env: `DATABASE_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBAPP_URL`, `JWT_SECRET`
4. Публичный HTTPS URL → в BotFather и в `TELEGRAM_WEBAPP_URL`

`DATABASE_URL` должен быть вида `postgresql+asyncpg://user:pass@host:5432/dbname`. Если хост даёт `postgres://...`, замени схему на `postgresql+asyncpg://`.

---

## Как устроен redeem

Mini App и бот ходят в одну и ту же логику.

Mini App:

1. Берёт `Telegram.WebApp.initData`
2. `POST /api/v1/promo-codes/redeem` с заголовком `Authorization: tma <initData>`
3. Сервер проверяет HMAC initData бот-токеном, находит/создаёт пользователя, атомарно гасит код

Бот `/redeem`:

1. Telegram уже подтвердил, кто пишет
2. Тот же `redeem_promo_code` в БД, без HTTP

Один код = один раз, с `SELECT FOR UPDATE`.

---

## Частые ошибки

| Симптом | Что проверить |
|---|---|
| Mini App пустой/не грузится | URL в BotFather должен заканчиваться на `/miniapp/` |
| 401 Invalid Telegram initData | Токен бота в `.env` не совпадает с ботом, который открыл WebApp |
| 503 Telegram auth is not configured | Пустой `TELEGRAM_BOT_TOKEN` |
| Кнопка WebApp не появляется | Пустой `TELEGRAM_WEBAPP_URL` или не HTTPS |
| Бот молчит | uvicorn запущен? токен верный? не два polling сразу |
| ngrok 403 / warning page | В бесплатном ngrok иногда нужна шапка; для Mini App лучше платный ngrok или сразу домен |
| Миграции не накатились | `alembic upgrade head` от имени проекта, не из другой папки |

---

## Порядок на фестиваль

1. Задеплоить API+бота на HTTPS-домен
2. Прописать URL в BotFather
3. Сгенерировать пачку кодов, распечатать CSV, CSV хранить оффлайн
4. Проверить 3 живых кода: Mini App, повтор, `/redeem`
5. Открыть бота посетителям

Локальный ngrok годится только для разработки. На фестиваль нужен стабильный домен.
