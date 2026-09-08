# Cola Fest — настройка, запуск, деплой

Пошагово: что уже сделано, что осталось сделать руками, и как всё проверить.

---

## 0. Что это и из чего состоит

Гейм-приложение для Coca-Cola: покупаешь напиток → вводишь код с крышки →
получаешь монеты → одеваешь своего белого медведя → вызываешь друзей на баттл
образов → подписчики голосуют (голос = 1 монета в призовой фонд) → победитель
забирает фонд и растит серию побед.

```
Telegram Bot ──уведомления──┐
                            ▼
Telegram Mini App / PWA ──HTTP──► FastAPI ──► PostgreSQL
Админ-панель ─────────────HTTP──►
```

Четыре контейнера, все в одном compose-проекте `cci`:

| контейнер | что делает |
|---|---|
| `cci-postgres` | база; наружу не торчит вообще |
| `cci-api` | REST API + отдаёт мини-апп и админку + миграции при старте |
| `cci-worker` | бот, доставка уведомлений, завершение баттлов, напоминания |
| `cci-tunnel` | Cloudflare Tunnel — единственный вход снаружи |

Адреса внутри одного домена:

| путь | что |
|---|---|
| `/app/` | мини-апп (он же PWA) — **этот URL идёт в BotFather** |
| `/admin-ui/` | админ-панель |
| `/docs` | Swagger по всему API |
| `/health` | живо ли приложение |
| `/health/db` | жива ли база |
| `/media/...` | картинки одежды и аватара |

---

## 1. Текущее состояние

**Работает прямо сейчас на https://cci.koblab.az**

- Сервер 89.117.49.72, код в `/opt/cci`, четыре контейнера подняты.
- Постоянный адрес через Cloudflare Tunnel, HTTPS с валидным сертификатом.
  Ни один порт хоста не занят — 80, 443 и 8080 по-прежнему у link2do и stride,
  их контейнеры не перезапускались.
- Бот `@cci_cocacola_bot` авторизован, кнопку меню выставил сам.
- Мини-апп: https://cci.koblab.az/app/ · Админка: https://cci.koblab.az/admin-ui/

**Осталось руками:**

1. Зарегистрировать Mini App в BotFather — раздел 5. Без этого приложение
   открывается по ссылке, но кнопки в чате не будет.
2. Сделать себе админа — раздел 7.
3. Нагенерить коды для крышек — раздел 8.

## 2. Локальная разработка (Windows)

### 2.1. База

```bash
docker run -d --name cci-dev-postgres -e POSTGRES_USER=cci -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=cci -p 55432:5432 postgres:16
```

### 2.2. Бекенд

Создай `.env` в корне проекта:

```
DATABASE_URL=postgresql+psycopg://cci:devpass@127.0.0.1:55432/cci
SECRET_KEY=любая-длинная-случайная-строка-для-локалки
ACCESS_TOKEN_EXPIRE_MINUTES=10080
TELEGRAM_BOT_TOKEN=123456:TEST_TOKEN_FOR_LOCAL_DEV_ONLY
TELEGRAM_WEBAPP_URL=
```

`TELEGRAM_BOT_TOKEN` локально может быть любой строкой — тесты подписывают
`initData` этим же значением, так что проверка HMAC проходит.

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -e ".[dev]"
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

Открой http://127.0.0.1:8000/docs — там весь API.

### 2.3. Фронтенды

```bash
cd miniapp && npm install && npm run build
```

```bash
cd admin && npm install && npm run build
```

После сборки FastAPI сам отдаёт их на `/app/` и `/admin-ui/`. Для разработки
с горячей перезагрузкой — `npm run dev` (порт 5173, проксирует API на 8000).

### 2.4. Тесты

Тесты — самостоятельные скрипты против **живой** базы, не pytest. Раннер
гоняет все и печатает один вердикт:

```bash
.venv/Scripts/python.exe scripts/run_tests.py
```

Один файл:

```bash
.venv/Scripts/python.exe scripts/run_tests.py telegram
```

Сейчас 31 скрипт, 823 проверки. Все зелёные.

### 2.5. Перерисовать одежду

Вся одежда — сгенерированные SVG. Правишь числа в скрипте, перегенеришь:

```bash
.venv/Scripts/python.exe scripts/generate_assets.py
```

Важное правило: **все слои рисуются в одной системе координат**
`viewBox="0 0 512 768"`. Поэтому аватар собирается простым наложением файлов
друг на друга, без единой строчки выравнивания. Новый предмет должен попадать
в «якорную зону» своего слота — они перечислены в шапке
`scripts/generate_assets.py`.

Заменить конкретную вещь на нормальную дизайнерскую картинку можно и без
деплоя — через админку, полем `image_url`.

---

## 3. Как это залито на сервер

Я скопировал туда `git archive` текущей ветки (только закоммиченные файлы, без
`node_modules`, `.venv` и `.env`). В GitHub **ничего не пушил**, как ты просил.

Обновить сервер после новых коммитов:

```bash
git archive --format=tar.gz -o cci.tar.gz HEAD
scp cci.tar.gz root@89.117.49.72:/opt/cci/
ssh root@89.117.49.72 'cd /opt/cci && tar xzf cci.tar.gz && rm cci.tar.gz && docker compose up -d --build'
```

`.env` при этом не затирается — его нет в архиве.

---

## 4. Домен и Cloudflare Tunnel

### Почему туннель, а не nginx

На сервере уже живут два чужих проекта: порт **80** держит nginx-контейнер
link2do, порт **443** — Caddy от stride. Чтобы повесить свой `server_name`,
пришлось бы править чужой прод.

Cloudflare Tunnel это обходит: `cloudflared` соединяется **изнутри наружу**,
портов на хосте не занимает вообще, HTTPS и сертификат даёт Cloudflare.
Telegram Mini App без HTTPS не работает, так что это ещё и решает вопрос
сертификата.

### Что уже сделано

Зона `koblab.az` уже была в Cloudflare, поэтому NS никуда не переносились и
записи корня и `www` не трогались — добавился ровно один CNAME для `cci`.

Туннель **locally-managed**: креды лежат в `/opt/cci/cloudflared` на сервере,
а не в дашборде. Так сделано потому, что панель Zero Trust просит привязать
карту даже на бесплатном тарифе, а этот путь идёт через обычный логин
Cloudflare и стоит ноль.

Как это было создано (повторять не нужно, записано на случай переезда):

```bash
CFD="docker run --rm -v /opt/cci/cloudflared:/home/nonroot/.cloudflared cloudflare/cloudflared:latest"

# каталог должен принадлежать uid 65532 — образ работает не от root,
# иначе `login` не сможет записать свой cert.pem уже ПОСЛЕ клика в браузере
mkdir -p /opt/cci/cloudflared && chown -R 65532:65532 /opt/cci/cloudflared

$CFD tunnel login                          # печатает ссылку, один клик в браузере
$CFD tunnel create cci
$CFD tunnel route dns cci cci.koblab.az    # создаёт CNAME
cd /opt/cci && docker compose --profile tunnel up -d
```

### Сменить адрес

```bash
docker run --rm -v /opt/cci/cloudflared:/home/nonroot/.cloudflared   cloudflare/cloudflared:latest tunnel route dns cci новый.домен
nano /opt/cci/.env          # TELEGRAM_WEBAPP_URL=https://новый.домен/app/
cd /opt/cci && docker compose --profile tunnel up -d
```

И обновить URL в BotFather — иначе Telegram продолжит открывать старый.

### Посмотреть без домена вообще

Быстрый туннель, без аккаунта и без токена:

```bash
cd /opt/cci && docker compose --profile preview up -d preview
docker compose logs preview | grep trycloudflare
```

Адрес меняется при каждом рестарте, поэтому только «посмотреть».
Выключить: `docker compose stop preview && docker compose rm -f preview`

## 5. Бот и Mini App в BotFather

Открой [@BotFather](https://t.me/BotFather).

### 5.1. Создать бота

```
/newbot
```

Имя (видно людям) и username (обязан заканчиваться на `bot`, например
`cci_cocacola_bot`). BotFather выдаст токен вида `123456789:AAE...` —
это `TELEGRAM_BOT_TOKEN`.

### 5.2. Создать Mini App

```
/newapp
```

- выбери своего бота
- Title: `Cola Fest`
- Description: любое
- иконка 640×360
- **Web App URL:** `https://cci.koblab.az/app/`
  — **со слэшем на конце и обязательно `/app/`**
- Short name: `colafest` (латиница)

### 5.3. Кнопка меню

```
/setmenubutton
```

Выбери бота → тот же URL `https://cci.koblab.az/app/`.

Бот при старте сам выставляет эту кнопку из `TELEGRAM_WEBAPP_URL`, но руками
надёжнее — Telegram иногда кеширует.

### 5.4. Команды

```
/setcommands
```

```
start - Открыть Cola Fest
redeem - Активировать код с крышки
me - Баланс и серия побед
```

---

## 6. .env на сервере

Уже заполнен, трогать не нужно. Для справки — что в нём и откуда:

| переменная | значение | откуда |
|---|---|---|
| `POSTGRES_PASSWORD` | сгенерирован | случайно при деплое |
| `SECRET_KEY` | сгенерирован | случайно при деплое, подписывает JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` | неделя |
| `TELEGRAM_BOT_TOKEN` | `8930791876:...` | BotFather |
| `TELEGRAM_BOT_USERNAME` | `cci_cocacola_bot` | BotFather |
| `TELEGRAM_WEBAPP_URL` | `https://cci.koblab.az/app/` | наш адрес |

`TUNNEL_TOKEN` не нужен: туннель работает на локальных кредах из
`/opt/cci/cloudflared` — см. раздел 4.

Файл с правами `600`, в git его нет и никогда не было.

После любой правки:

```bash
cd /opt/cci && docker compose --profile tunnel up -d
docker compose logs worker --tail 20
```

Признак, что всё сошлось:

```
Telegram bot authorised as @cci_cocacola_bot
Menu button points at https://cci.koblab.az/app/
Notification delivery loop started
```

> ⚠️ Токен бота в `.env` и бот, в котором открыт Mini App, должны быть **одним
> и тем же ботом**. Иначе подпись `initData` не сойдётся и мини-апп будет
> получать 401 на каждый запрос.

## 7. Сделать себе админа

Админом нельзя стать через API — только через базу. Это специально: тогда нет
эндпоинта, которым обычный игрок мог бы себя повысить.

1. Зарегистрируй обычный аккаунт с почтой и паролем (админка входит по ним,
   не через Telegram):

```bash
curl -X POST https://cci.koblab.az/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","email":"admin@example.com","password":"длинный-пароль"}'
```

2. Повысь его:

```bash
ssh root@89.117.49.72
docker exec cci-postgres psql -U cci -d cci -c "UPDATE users SET is_admin = true WHERE username = 'admin';"
```

3. Заходи на `https://cci.koblab.az/admin-ui/` этой же парой.

В админке: пользователи, продукты, QR-коды, одежда (включая замену картинок).

---

## 8. Коды для крышек

Один код = одно погашение = монеты. Хранится в таблице `qr_codes`.

Через админку: **QR Codes → Create**, там же выбирается продукт и номинал.

Пачкой через SQL (например 1000 кодов по 50 монет):

```bash
docker exec cci-postgres psql -U cci -d cci -c "
INSERT INTO products (name, sku) VALUES ('Coca-Cola 0.5', 'CC-05L')
ON CONFLICT (sku) DO NOTHING;

INSERT INTO qr_codes (code, product_id, coin_value)
SELECT
  'CF-' || upper(substr(md5(random()::text || g::text), 1, 8)),
  (SELECT product_id FROM products WHERE sku = 'CC-05L'),
  50
FROM generate_series(1, 1000) g
ON CONFLICT (code) DO NOTHING;
"
```

Выгрузить в CSV для печати:

```bash
docker exec cci-postgres psql -U cci -d cci -A -F',' -c \
  "SELECT code, coin_value FROM qr_codes WHERE status = 'ACTIVE' ORDER BY created_at DESC" \
  > /opt/cci/codes.csv
```

Что важно знать про коды:

- Ввод **нечувствителен к регистру и пробелам**: `cf-a1b2 c3d4` погасит
  `CF-A1B2C3D4`. Люди набирают их руками с крышки.
- Погасить можно ровно один раз. Второй раз — 409, даже если два человека
  жмут одновременно (строка блокируется на время транзакции).
- Один код = 50 монет = примерно треть дешёвой вещи в магазине. Самая дорогая
  вещь, Bear Paws за 900, — это 18 крышек, цель на весь фестиваль.

---

## 9. Проверка, что всё живо

### На сервере

```bash
cd /opt/cci
docker compose ps                  # четыре контейнера, api и postgres healthy
docker compose logs api --tail 30
docker compose logs worker --tail 30
```

### Снаружи

```bash
curl https://cci.koblab.az/health        # {"status":"ok"}
curl https://cci.koblab.az/health/db     # {"database":"ok","result":1}
curl -I https://cci.koblab.az/app/       # 200
curl -I https://cci.koblab.az/admin-ui/  # 200
```

### С телефона, полный путь

Проверять лучше с двух аккаунтов — баттл в одиночку не сделать.

1. Напиши боту `/start` → кнопка **Открыть Cola Fest** → мини-апп грузится,
   виден медведь и баланс 0.
2. **Ввести код с крышки** → введи код → баланс вырос.
3. **Магазин** → тапни вещь → она появилась на медведе в превью → **Купить** →
   баланс упал.
4. **Гардероб** → тапни вещь → **Надеть** → медведь переоделся.
5. **Друзья** → найди второй аккаунт → **Подписаться** → **⚔️ Вызвать** →
   выбери 30 минут.
6. На втором аккаунте: приходит сообщение от бота **и** вызов на вкладке
   **Баттлы → Мои** → **Принять**.
7. Первому приходит «принял твой вызов».
8. С третьего аккаунта (или второго, если он не участник) — **Баттлы →
   Другие** → открой баттл → **За …** → списалась монета, счёт изменился,
   призовой фонд вырос.
9. Через 10 минут до конца обоим участникам приходит «баттл заканчивается».
10. По истечении — «ты выиграл / проиграл», победителю начислен фонд, серия
    побед выросла, у проигравшего обнулилась. Видно в **Лидерах**.

Ускорить шаг 10 для теста (сдвинуть старт баттла на час назад):

```bash
docker exec cci-postgres psql -U cci -d cci -c \
  "UPDATE competitions SET start_time = start_time - interval '2 hours' WHERE status_id = (SELECT status_id FROM competition_status WHERE status_name='active');"
```

Воркер подметает каждые 30 секунд.

---

## 10. Если что-то не работает

| симптом | причина |
|---|---|
| мини-апп открывается, но всё 401 | токен в `.env` от другого бота, чем тот, где открыт Mini App |
| кнопка в боте не открывает приложение | URL не `https`, или не заканчивается на `/app/`, или в BotFather другой URL |
| бот молчит | `TELEGRAM_BOT_TOKEN` пуст → `docker compose logs worker` скажет «running without the bot» |
| уведомления не приходят | человек не нажимал `/start` у бота — Telegram запрещает писать первым. В базе они копятся и уйдут, как только он напишет |
| домен не отвечает | `docker compose logs tunnel`; проверь, что Public Hostname указывает на `api:8000`, а не на `localhost` |
| `/admin-ui/` даёт 404 | образ собран без фронта: `docker compose up -d --build` |
| сканер QR не открывается в браузере | в Safari нет `BarcodeDetector`. В Telegram работает всегда; в браузере — вводи код руками, поле всегда на экране |
| после деплоя старая версия | `docker compose up -d --build`, без `--build` пересборки не будет |

Логи одной командой:

```bash
cd /opt/cci && docker compose logs -f --tail 50
```

---

## 11. Чего сознательно не делал

- **Не пушил в GitHub** — всё локально в ветке
  `claude/polarbear-telegram-integration-38f89b`, семь коммитов.
- **Не трогал чужие проекты**: `/opt/link2do`, `/root/link2do-backend`,
  `/opt/stride`. Их порты 80/443/8080 не занимал, конфиги не читал и не правил.
- **Не поднимал публичный туннель** — это публичный адрес, включишь сам, когда
  будет нужно (раздел 4.3 или 4.4).
- **Не решал проблему из ТЗ п.7** («штрихкод не уникален для бутылки») — это
  вопрос к Coca-Cola, а не к коду. MVP работает на уникальных кодах под
  крышкой, как в ТЗ и написано.
- **Web Push для PWA** — вне MVP, уведомления идут через бота.
- **Декодер QR в браузере (wasm)** — ~200 КБ на каждую загрузку ради случая
  «Safari вне Telegram». В Telegram сканер нативный. Стоит вернуться к этому,
  если PWA станет реальной точкой входа.

---

## 12. Отдельно про безопасность

- Root-пароль сервера прошёл открытым текстом в чате. Смени его и перейди на
  SSH-ключ.
- `SECRET_KEY` и пароль базы на сервере сгенерированы случайно и лежат только
  в `/opt/cci/.env` с правами `600`. В git их нет.
- У чужого репозитория `Uzeyir44/PolarBear`, чей бекенд лёг в основу, **нет
  файла лицензии**. Перед публичным релизом стоит взять у автора явное
  разрешение или договориться о лицензии.
