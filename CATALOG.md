# Как наполнять каталог одежды

Этот файл — для тебя короткая инструкция, а дальше — техзадание, которое можно
целиком отдать другому ИИ.

**Что происходит.** В приложении есть медведь и шесть слотов одежды: волосы,
головной убор, верх, низ, обувь, очки. Сейчас в каталоге 24 вещи, которые
нарисовал я. Чтобы каталог рос, не нужен ни доступ к серверу, ни админка — есть
эндпоинт, который принимает вещь одним HTTP-запросом: имя, слот, цена и сам
рисунок в формате SVG прямо в теле запроса. Сервер проверяет рисунок, кладёт
его на диск, сам делает миниатюру для витрины и заводит вещь в магазине. Через
пару секунд её видно в приложении.

**Что нужно сделать тебе:**

1. Придумать ключ и вписать его на сервере в `/opt/cci/.env` строкой
   `CATALOG_API_KEY=...`, затем `cd /opt/cci && docker compose up -d`.
   Без ключа запись отключена — эндпоинт отвечает 503. Читать (`/catalog/spec`
   и `/catalog/items`) можно и без ключа.
2. Отдать другому ИИ **всё, что ниже разделителя**, и сам ключ.

**Чем это отличается от админки.** Админка — для человека с браузером и для
вещей, картинки которых уже лежат на сервере. Этот эндпоинт — для того, кто
умеет только слать JSON. Обе двери ведут в один и тот же каталог.

**Что делать с плохой вещью.** Пока её никто не купил — `DELETE`, и она
исчезнет вместе с файлами. Если уже купили — удалять нельзя (человек заплатил
монеты), но можно `PATCH` перерисовать её на месте или спрятать из магазина,
поставив `availability_status: "unavailable"`.

---

# Cola Fest — clothing contribution brief

You are drawing clothing for a Telegram Mini App. The character is a white
polar bear; players earn coins from bottle caps and spend them on these items,
then dress up and battle each other on outfits.

Base URL: `https://cci.koblab.az`
Write header: `X-Catalog-Key: <the key you were given>`

## Read this first, from the running system

```bash
curl https://cci.koblab.az/catalog/spec
curl https://cci.koblab.az/catalog/items
```

`/catalog/spec` returns the canvas, every slot with its anchor box and
thumbnail crop, the palette, and the rules — as data. It is generated from the
live server, so where this document and that response disagree, **the response
is right**. `/catalog/items` is everything already drawn; read it before you
start so you do not redraw a Fest Tee that exists.

## The one idea that makes this work

Every layer — the bear, and every garment — is an SVG with the **same**
`viewBox="0 0 512 768"`, and each garment is drawn **where it belongs on the
bear** inside that shared space.

There is no positioning step afterwards. Rendering an outfit is literally
stacking the files on top of each other. So a hat is not "a hat drawing" that
gets placed on the head later — it is a drawing whose hat shape sits at the
head's coordinates, on an otherwise empty 512×768 canvas.

Get this wrong and the item still uploads, still passes validation, and looks
like a hat floating next to the bear's knee.

## Where each slot goes

Stay inside your slot's box. The layer order is what the app paints back to
front, and it explains a few of the boxes: hair is painted before hats so a cap
sits on the hair, and glasses are painted last because they belong in front of
everything on the face.

| slot | anchor box (x, y, w, h) | painted | what goes here |
|---|---|---|---|
| `bottom` | 166, 440, 180, 210 | 1st | shorts, trousers, skirts |
| `top` | 146, 255, 220, 230 | 2nd | tees, hoodies, jackets |
| `shoes` | 156, 620, 200, 110 | 3rd | sneakers, boots |
| `hair` | 156, 60, 200, 200 | 4th | hairstyles |
| `hat` | 156, 40, 200, 200 | 5th | caps, buckets, crowns |
| `accessory` | 196, 150, 120, 50 | 6th | glasses, visors |

Useful landmarks on the bear: the head is centred at x≈256 and spans roughly
y 90–250; the shoulders are at y≈270; the waist at y≈450; the feet rest at
y≈730. The bear is symmetrical about x=256, so centre your shapes there unless
you mean not to.

## Style

The 24 existing items are one coherent set, and a new item has to look like it
belongs to that set, not like a better drawing next to it.

- **Flat vector.** Two tones per shape: a base colour and one darker shade for
  the part in shadow. No gradients, no outlines, no filters, no textures.
- **Silhouette first.** The item is 60 px tall on a phone. If it does not read
  as a hoodie from across the room, detail will not save it.
- **Rounded corners**, roughly `rx="12"`, consistently.
- **Transparent background.** The bear is drawn underneath by the app. Do not
  paint a backdrop, and do not draw the bear.
- **Palette** — take it from `/catalog/spec`. The core of it:

  | | |
  |---|---|
  | red `#E4002B` / deep `#A5001F` | the Coca-Cola red, the anchor of the set |
  | white `#FFFFFF` | |
  | fur `#F4EFE6` / shade `#DCD3C4` | the bear's own colours |
  | ink `#1A1A1A` | |
  | gold `#F2C230` / deep `#E0A81E` | |
  | denim `#4A6FA5` / deep `#33527E` | |
  | slate `#3C4652` / deep `#2A323C` | |
  | ice `#BFE3F2` / deep `#8CC4DC` | |
  | mint `#37C2A6` / deep `#28A48C` | |
  | olive `#6E7A4F` / deep `#57603D` | |

  Colours outside this list are allowed but should be rare and deliberate.

## What the SVG must be

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768" fill="none">
  <!-- shapes and paths only -->
</svg>
```

Hard requirements, each enforced by the server:

- Root element `<svg>`, `viewBox="0 0 512 768"` exactly. No `width`/`height`.
- Shapes and paths only. `<script>`, `<image>`, `<foreignObject>`, `<iframe>`,
  `<object>`, `<embed>`, `<video>`, `<audio>`, `<set>`, `<handler>` are all
  refused.
- No event attributes (`onload`, `onclick`, anything starting with `on`).
- Nothing may reference another address. `href` and `src` may only point at a
  `#id` in the same file; `url(...)` likewise. Define gradients and filters
  inline if you use them at all.
- No `<!DOCTYPE>` and no `<!ENTITY>`. Send the `<svg>` element alone.
- Under 256 KB. Real items in this style are 1–4 KB; anything near the limit
  means a traced photo, which will not match the set anyway.

Do **not** send a thumbnail. It is derived from your drawing — the same shapes
with the viewBox narrowed to your slot's crop — so it can never disagree with
what the avatar actually wears.

## Naming

Names are shown untranslated in Russian, English and Azerbaijani, because they
are product names rather than sentences. So:

- English, two or three words: `Fest Tee`, `Polar Snapback`, `Cola Aviators`.
- Concrete, not abstract. `Frost Runners` beats `Cool Shoes #3`.
- Unique across the whole catalog, case-insensitively. A duplicate is a 409.
- No emoji, no numbering, no brand names other than the Cola Fest ones already
  in use.

The filename is derived from the name, so you never choose one.

## Pricing

One bottle cap is **50 coins**. A price is really a statement about how many
drinks the item costs, so pick from the tiers rather than inventing numbers:

| tier | coins | caps | meaning |
|---|---|---|---|
| cheap | 150–250 | 3–5 | something a new player gets on day one |
| mid | 300–450 | 6–9 | a considered purchase |
| expensive | 500–700 | 10–14 | a goal for the week |
| trophy | 800–1000 | 16–20 | one per slot at most, for the whole festival |

Keep the mix weighted towards cheap and mid. A catalog where everything is a
trophy is a catalog where nobody buys anything.

## Submitting

```bash
curl -X POST https://cci.koblab.az/catalog/items \
  -H "Content-Type: application/json" \
  -H "X-Catalog-Key: YOUR_KEY" \
  -d '{
    "name": "Fest Tee",
    "slot": "top",
    "price": 150,
    "description": "Festival tee in Cola red.",
    "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 512 768\" fill=\"none\"><rect x=\"160\" y=\"270\" width=\"192\" height=\"200\" rx=\"12\" fill=\"#E4002B\"/><rect x=\"160\" y=\"430\" width=\"192\" height=\"40\" fill=\"#A5001F\"/></svg>"
  }'
```

`slot` is one of `hair`, `hat`, `top`, `bottom`, `shoes`, `accessory`. You never
supply a category id — the slot picks the category, which is the point: a wrong
id would silently put a hat on someone's feet.

A `201` comes back with the item, its `image_url` and its `thumb_url`.

### Fixing one

```bash
# redraw in place — the URL does not change, so everyone who already owns
# the item sees the new drawing
curl -X PATCH https://cci.koblab.az/catalog/items/<item_id> \
  -H "Content-Type: application/json" -H "X-Catalog-Key: YOUR_KEY" \
  -d '{"svg": "<svg ...>", "price": 200}'

# hide it from the shop without taking it from anyone's wardrobe
curl -X PATCH https://cci.koblab.az/catalog/items/<item_id> \
  -H "Content-Type: application/json" -H "X-Catalog-Key: YOUR_KEY" \
  -d '{"availability_status": "unavailable"}'

# delete it — only works while nobody owns or wears it
curl -X DELETE https://cci.koblab.az/catalog/items/<item_id> \
  -H "X-Catalog-Key: YOUR_KEY"
```

## Check your work

Do not submit fifty items and hope. After the first one:

1. `curl https://cci.koblab.az/media/uploads/top/fest-tee.svg` — the layer.
2. `curl https://cci.koblab.az/media/uploads/top/fest-tee.thumb.svg` — the shop
   thumbnail. If the item is a speck in the corner or cropped in half, your
   shapes are outside the anchor box.
3. Open `https://cci.koblab.az/app/` and look at it on the bear. This is the
   only check that catches "it uploaded fine and sits on his knee".

Then submit the rest.

## Errors you will see

| code | meaning |
|---|---|
| 503 | `CATALOG_API_KEY` is not set on the server. Nothing you can fix from here. |
| 401 | Missing or wrong `X-Catalog-Key`. |
| 422 | The drawing was refused. The `detail` field says exactly what to change — read it, it is written for you, not for a log file. |
| 409 | On create: that name is taken. On delete: players already own the item; `PATCH` it to `unavailable` instead. |
| 404 | No such item id. |

## A worked example

A hoodie. Note that every coordinate is an absolute position on the bear, that
the second colour is only ever the shadow of the first, and that the whole
thing is six shapes.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768" fill="none">
  <!-- body -->
  <rect x="150" y="262" width="212" height="215" rx="16" fill="#37C2A6"/>
  <!-- sleeves -->
  <rect x="132" y="272" width="46" height="150" rx="20" fill="#37C2A6"/>
  <rect x="334" y="272" width="46" height="150" rx="20" fill="#37C2A6"/>
  <!-- hood, behind the neck -->
  <path d="M196 268 Q256 232 316 268 Q256 296 196 268 Z" fill="#28A48C"/>
  <!-- hem, in shadow -->
  <rect x="150" y="443" width="212" height="34" rx="14" fill="#28A48C"/>
  <!-- pocket -->
  <rect x="206" y="372" width="100" height="52" rx="12" fill="#28A48C"/>
</svg>
```
