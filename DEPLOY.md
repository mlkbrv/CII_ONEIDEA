# CCI — деплой на сервере и настройка Telegram Mini App

Порты на хосте специально нестандартные, чтобы не пересечься с другими проектами:

- API / Mini App: **18080** (внутри контейнера 8000)
- Postgres: **не торчит наружу**, только внутри docker-сети CCI на 5432

Nginx/Caddy других проектов на 80/443 не трогаем. Для CCI добавляется отдельный `server_name`.

---

## 1. На сервере

В папке проекта создай `.env`:

```env
TELEGRAM_BOT_TOKEN=123456:AA_токен_от_BotFather
TELEGRAM_WEBAPP_URL=https://cci.твой-домен.com/oneidea/
JWT_SECRET=длинный-случайный-секрет-хотя-бы-32-символа
PROMO_CODE_PEPPER=ещё-одна-случайная-строка
```

`TELEGRAM_WEBAPP_URL` должен быть **https** и заканчиваться на `/oneidea/`.

Запуск:

```bash
docker compose up -d --build
curl http://127.0.0.1:18080/health
```

Должно ответить `{"status":"ok"}`.

Прокси на домен (пример nginx). Слушаем 80/443 как обычно, бэкенд — **18080**:

```nginx
server {
    listen 80;
    server_name cci.твой-домен.com;

    location / {
        proxy_pass http://127.0.0.1:18080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo certbot --nginx -d cci.твой-домен.com
```

Проверка в браузере:

- `https://cci.твой-домен.com/health`
- `https://cci.твой-домен.com/oneidea/` — должна открыться страница промокода

---

## 2. Telegram: бот

1. Открой [@BotFather](https://t.me/BotFather)
2. `/newbot` → имя и username
3. Скопируй токен в `.env` как `TELEGRAM_BOT_TOKEN`
4. Перезапусти API, если токен вписал после старта:

```bash
docker compose up -d
```

Команды:

```
/setcommands
```

```
start - Открыть Cola Fest
redeem - Активировать промокод
```

---

## 3. Telegram Mini App — это главное

Telegram открывает не «сайт», а Web App по HTTPS URL. Без этого шага кнопка в боте не заработает.

URL, который везде должен быть **один и тот же**:

```
https://cci.твой-домен.com/oneidea/
```

Слэш в конце обязателен.

### 3.1. Создать Mini App

В BotFather:

1. `/newapp`
2. Выбери своего бота
3. Title: `CCI`
4. Short name: `cci` (латиница, без пробелов)
5. **Web App URL:** `https://cci.твой-домен.com/oneidea/`
6. Описание и иконка — по желанию

### 3.2. Кнопка меню у бота

В BotFather:

1. `/mybots` → твой бот → **Bot Settings** → **Menu Button**
2. Включи кнопку
3. Текст: `CCI`
4. URL: `https://cci.твой-домен.com/oneidea/`

Или командой:

```
/setmenubutton
```

Тот же URL.

### 3.3. Согласовать `.env`

В `.env` на сервере:

```env
TELEGRAM_WEBAPP_URL=https://cci.твой-домен.com/oneidea/
```

Ровно тот URL, что в BotFather. Потом:

```bash
docker compose up -d
```

Бот при старте сам ставит menu button на этот URL. Если URL пустой — кнопки «Открыть приложение» не будет.

---

## 4. Как пользоваться после настройки

- Написать боту `/start` → кнопка **Открыть приложение** → ввести/сканировать код
- Либо в чате: `/redeem КОД`

Mini App шлёт `Authorization: tma <initData>`. Токен бота в `.env` должен быть **того же бота**, в котором открыт Web App. Иначе будет 401.

---

## 5. Коды для банок

```bash
docker compose exec api python scripts/generate_promo_codes.py --count 1000 --coin-reward 50 --output /tmp/promo_codes.csv
docker compose cp cci-api:/tmp/promo_codes.csv ./promo_codes.csv
```

CSV — plaintext для печати. В БД только хеши.

---

## Если Mini App не открывается

- URL не https
- URL без `/oneidea/`
- BotFather и `.env` содержат разные URL
- nginx не проксирует на `127.0.0.1:18080`
- certbot не выписал сертификат на этот `server_name`
- токен в `.env` от другого бота
