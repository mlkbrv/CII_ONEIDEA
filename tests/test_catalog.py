"""
End-to-end checks of the catalog submission API (/catalog).

    python -m tests.test_catalog

Covers:
  - Key handling: writes rejected without the key, with a wrong key, and
    disabled entirely (503) when no key is configured on the server.
  - The spec: canvas, one entry per slot with its anchor and thumbnail crop,
    live item counts.
  - SVG validation, which is the point of the whole module — wrong viewBox,
    <script>, event attributes, external href, external url(), url()/@import
    hidden inside <style> text, processing instructions, XML comments,
    DOCTYPE entities, oversize, malformed XML. Each must be REFUSED, because
    the file is written to disk and then served to every player. A plain
    <?xml ...?> declaration is the one processing instruction allowed through
    — real editors emit it routinely.
  - Create: the item lands in the shop, the layer and the derived thumbnail
    are both on disk, the thumbnail carries the slot's crop and the same
    shapes, and the slot picks the category (a contributor never sees an id).
  - Name collisions -> 409, including a genuine race between two concurrent
    identical submissions: exactly one must land, never two rows sharing a
    name. Two different names that slugify to the same string race for the
    same file: exactly one wins, the other gets a clean 409, never a silently
    overwritten picture.
  - Patch: art replaced under the SAME url, so a wardrobe that already holds
    the item shows the new drawing.
  - Delete: refused (409) while a player owns the item, allowed otherwise,
    and the files go with it.

Everything created is removed afterwards, including files.
"""
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.database import SessionLocal
from app.main import app
from app.models import ClothingItem, User, UserWardrobe
from app.services import catalog_art

# Raised when the client is used, not when it is imported, so filtering here
# is early enough and keeps every import at the top of the file.
warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

RUN_ID = f"{int(time.time())}{uuid.uuid4().hex[:6]}"
KEY = f"test-catalog-key-{RUN_ID}"
AUTH = {"X-Catalog-Key": KEY}

# The smallest thing that is a legitimate submission: one shape, on the
# canvas, inside the "top" anchor box.
GOOD_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768" fill="none">'
    '<rect x="160" y="270" width="192" height="200" rx="12" fill="#E4002B"/>'
    '<rect x="160" y="430" width="192" height="40" fill="#A5001F"/>'
    "</svg>"
)

REJECTED = [
    (
        "wrong viewBox",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="10" height="10"/></svg>',
        "viewBox",
    ),
    (
        "<script>",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><script>alert(1)</script></svg>',
        "script",
    ),
    (
        "event attribute",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><rect onload="x()" width="1" height="1"/></svg>',
        "onload",
    ),
    (
        "external href",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><a href="https://evil.example/x"><rect width="1" height="1"/></a></svg>',
        "href",
    ),
    (
        "external url() reference",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><rect width="1" height="1" fill="url(https://evil.example/g.svg#a)"/></svg>',
        "url(",
    ),
    (
        "embedded bitmap",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><image href="#x" width="1" height="1"/></svg>',
        "image",
    ),
    (
        "DOCTYPE with entities",
        '<!DOCTYPE svg [<!ENTITY a "boom">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><rect width="1" height="1"/></svg>',
        "DOCTYPE",
    ),
    (
        "not well-formed",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><rect>',
        "well-formed",
    ),
    (
        "not an <svg> root",
        '<div viewBox="0 0 512 768"></div>',
        "root element",
    ),
    (
        "processing instruction",
        '<?xml-stylesheet type="text/css" href="https://evil.example/x.css"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768"><rect width="1" height="1"/></svg>',
        "processing instruction",
    ),
    (
        "XML comment",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768">'
        "<!-- <script>alert(1)</script> --><rect width=\"1\" height=\"1\"/></svg>",
        "comment",
    ),
    (
        "external url() inside <style>",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768">'
        '<style>.a{fill:url(https://evil.example/g.svg#a)}</style>'
        '<rect class="a" width="1" height="1"/></svg>',
        "style",
    ),
    (
        "@import inside <style>",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 768">'
        '<style>@import url(https://evil.example/x.css);</style>'
        '<rect width="1" height="1"/></svg>',
        "@import",
    ),
]

results: list[tuple[str, bool, str]] = []
created_item_ids: list[uuid.UUID] = []
created_user_ids: list[uuid.UUID] = []
written_paths: list = []


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def cleanup() -> None:
    with SessionLocal() as db:
        for user_id in created_user_ids:
            db.execute(delete(UserWardrobe).where(UserWardrobe.user_id == user_id))
            user = db.get(User, user_id)
            if user is not None:
                db.delete(user)
        db.commit()
        for item_id in created_item_ids:
            item = db.get(ClothingItem, item_id)
            if item is not None:
                catalog_art.remove(item.image_url)
                db.delete(item)
        db.commit()
    for path in written_paths:
        path.unlink(missing_ok=True)


original_key = settings.catalog_api_key
try:
    # --- The door is shut when no key is configured ----------------------
    settings.catalog_api_key = ""
    response = client.post(
        "/catalog/items",
        json={"name": "x", "slot": "top", "price": 10, "svg": GOOD_SVG},
    )
    results.append(
        ("no key configured -> 503, not an open endpoint", response.status_code == 503, str(response.status_code))
    )

    settings.catalog_api_key = KEY

    response = client.post(
        "/catalog/items", json={"name": "x", "slot": "top", "price": 10, "svg": GOOD_SVG}
    )
    results.append(("missing key -> 401", response.status_code == 401, str(response.status_code)))

    response = client.post(
        "/catalog/items",
        headers={"X-Catalog-Key": "wrong"},
        json={"name": "x", "slot": "top", "price": 10, "svg": GOOD_SVG},
    )
    results.append(("wrong key -> 401", response.status_code == 401, str(response.status_code)))

    # --- Reading is open --------------------------------------------------
    response = client.get("/catalog/spec")
    spec = response.json()
    results.append(("GET /catalog/spec is open -> 200", response.status_code == 200, str(response.status_code)))
    results.append(("spec states the shared canvas", spec.get("canvas_view_box") == "0 0 512 768", str(spec.get("canvas_view_box"))))
    slots = {entry["slot"]: entry for entry in spec.get("slots", [])}
    results.append(("spec covers all six slots", set(slots) == {"hair", "hat", "top", "bottom", "shoes", "accessory"}, str(sorted(slots))))
    results.append(
        (
            "each slot carries an anchor box and a thumbnail crop",
            all(entry["anchor"]["width"] > 0 and entry["thumb_view_box"] for entry in slots.values()),
            "",
        )
    )
    results.append(("spec publishes the palette", len(spec.get("palette", {})) >= 8, str(len(spec.get("palette", {})))))

    response = client.get("/catalog/items")
    results.append(("GET /catalog/items is open -> 200", response.status_code == 200, str(response.status_code)))
    baseline_total = response.json()["total"]
    results.append(("the 24 shipped items are listed", baseline_total >= 24, str(baseline_total)))

    # --- Everything that must be refused ---------------------------------
    for label, svg, fragment in REJECTED:
        response = client.post(
            "/catalog/items",
            headers=AUTH,
            json={"name": f"Bad {label} {RUN_ID}", "slot": "top", "price": 10, "svg": svg},
        )
        refused = response.status_code == 422
        explained = fragment.lower() in str(response.json().get("detail", "")).lower()
        results.append((f"refuse {label} -> 422", refused, str(response.status_code)))
        results.append((f"refusal for {label} says what to fix", refused and explained, str(response.json().get("detail"))[:80]))

    oversize = GOOD_SVG.replace(
        "</svg>", "<rect width='1' height='1' fill='#000000'/>" * 9000 + "</svg>"
    )
    response = client.post(
        "/catalog/items",
        headers=AUTH,
        json={"name": f"Huge {RUN_ID}", "slot": "top", "price": 10, "svg": oversize},
    )
    results.append(("refuse oversize SVG -> 422", response.status_code == 422, str(response.status_code)))

    # A plain XML declaration is the one processing instruction allowed
    # through — real SVG editors emit it routinely, so it must not be caught
    # by the same net as <?xml-stylesheet ...?>.
    with_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n' + GOOD_SVG
    response = client.post(
        "/catalog/items",
        headers=AUTH,
        json={"name": f"XmlDecl {RUN_ID}", "slot": "top", "price": 10, "svg": with_declaration},
    )
    decl_ok = response.status_code == 201
    results.append(("a plain <?xml ...?> declaration is allowed through -> 201", decl_ok, str(response.status_code)))
    if decl_ok:
        decl_item = response.json()
        created_item_ids.append(uuid.UUID(decl_item["item_id"]))
        written_paths.append(catalog_art.UPLOAD_DIR / decl_item["image_url"].split("/media/uploads/", 1)[1])

    # --- The happy path ---------------------------------------------------
    name = f"Test Fest Tee {RUN_ID}"
    response = client.post(
        "/catalog/items",
        headers=AUTH,
        json={
            "name": f"  {name}  ",
            "slot": "top",
            "price": 150,
            "svg": GOOD_SVG,
            "description": "A test item.",
        },
    )
    created = response.json()
    ok_created = response.status_code == 201
    results.append(("create a valid item -> 201", ok_created, str(response.status_code) + " " + str(created)[:120]))

    if not ok_created:
        raise SystemExit("cannot continue without a created item")

    item_id = uuid.UUID(created["item_id"])
    created_item_ids.append(item_id)

    results.append(("name is trimmed", created["name"] == name, created["name"]))
    results.append(("slot picked the category, contributor never saw an id", created["category_name"] == "Tops", created["category_name"]))
    results.append(("image_url is under the uploads prefix", created["image_url"].startswith("/media/uploads/top/"), created["image_url"]))
    results.append(("thumb_url follows the app's convention", created["thumb_url"] == created["image_url"].replace(".svg", ".thumb.svg"), created["thumb_url"]))

    layer = catalog_art.UPLOAD_DIR / created["image_url"].split("/media/uploads/", 1)[1]
    thumb = layer.with_name(layer.name.replace(".svg", ".thumb.svg"))
    written_paths.extend([layer, thumb])
    results.append(("the layer is on disk", layer.is_file(), str(layer)))
    results.append(("the thumbnail is on disk", thumb.is_file(), str(thumb)))

    if thumb.is_file():
        thumb_text = thumb.read_text(encoding="utf-8")
        results.append(('thumbnail carries the slot crop, not the full canvas', 'viewBox="100 240 312 260"' in thumb_text, thumb_text[:70]))
        results.append(("thumbnail keeps the same shapes as the layer", 'x="160" y="270"' in thumb_text, ""))

    # Served over HTTP, not merely written.
    results.append(("the layer is served by /media", client.get(created["image_url"]).status_code == 200, ""))
    results.append(("the thumbnail is served by /media", client.get(created["thumb_url"]).status_code == 200, ""))

    # Visible to players, which is the only reason any of this exists. The
    # shop needs a signed-in player, so this browses it as one rather than
    # asserting against the contributor-facing list it was just created in.
    shopper = f"catshop_{RUN_ID}"
    client.post(
        "/auth/register",
        json={"username": shopper, "email": f"{shopper}@example.com", "password": "SuperSecret123!"},
    )
    token = client.post(
        "/auth/login", json={"username": shopper, "password": "SuperSecret123!"}
    ).json().get("access_token")
    with SessionLocal() as db:
        row = db.execute(select(User.user_id).where(User.username == shopper)).scalar_one_or_none()
        if row is not None:
            created_user_ids.append(row)

    shop = client.get("/clothing", headers={"Authorization": f"Bearer {token}"}).json()
    shop_names = {entry["name"] for entry in shop.get("items", [])}
    results.append(("the item appears in the public shop", name in shop_names, str(shop.get("total"))))

    # --- Collisions -------------------------------------------------------
    response = client.post(
        "/catalog/items",
        headers=AUTH,
        json={"name": name, "slot": "top", "price": 150, "svg": GOOD_SVG},
    )
    results.append(("duplicate name -> 409", response.status_code == 409, str(response.status_code)))

    # Same slug, different name: must succeed, with a distinct file.
    response = client.post(
        "/catalog/items",
        headers=AUTH,
        json={"name": f"Test-Fest-Tee-{RUN_ID}", "slot": "top", "price": 150, "svg": GOOD_SVG},
    )
    twin_ok = response.status_code == 201
    results.append(("colliding slug still creates -> 201", twin_ok, str(response.status_code)))
    if twin_ok:
        twin = response.json()
        created_item_ids.append(uuid.UUID(twin["item_id"]))
        written_paths.append(catalog_art.UPLOAD_DIR / twin["image_url"].split("/media/uploads/", 1)[1])
        results.append(("colliding slug got its own file", twin["image_url"] != created["image_url"], twin["image_url"]))

    # --- The actual race, not just the sequential check ------------------
    # Two threads, same name, fired together: this is what _name_taken()
    # cannot catch on its own — both can pass it before either commits. The
    # invariant that has to hold regardless of which one the scheduler lets
    # through first: exactly one 201, exactly one 409, and the database ends
    # up with exactly one row under that name.
    race_name = f"Race Name {RUN_ID}"

    def submit_same_name():
        return client.post(
            "/catalog/items",
            headers=AUTH,
            json={"name": race_name, "slot": "top", "price": 10, "svg": GOOD_SVG},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        race_responses = list(pool.map(lambda _: submit_same_name(), range(2)))
    race_codes = sorted(r.status_code for r in race_responses)
    results.append(
        (
            "concurrent identical names: exactly one 201 and one 409",
            race_codes == [201, 409],
            str(race_codes),
        )
    )
    winner = next((r for r in race_responses if r.status_code == 201), None)
    if winner is not None:
        won = winner.json()
        created_item_ids.append(uuid.UUID(won["item_id"]))
        written_paths.append(catalog_art.UPLOAD_DIR / won["image_url"].split("/media/uploads/", 1)[1])
    with SessionLocal() as db:
        row_count = db.execute(
            select(func.count()).select_from(ClothingItem).where(
                func.lower(ClothingItem.name) == race_name.lower()
            )
        ).scalar_one()
    results.append(("the database holds exactly one row under that name", row_count == 1, str(row_count)))

    # Two DIFFERENT names that fold to the same slug ("Race Slug X" and
    # "Race-Slug X" both -> "race-slug-x"): the unique index on name cannot
    # catch this, only the exclusive file create in catalog_art.write() can.
    slug_name_a = f"Race Slug {RUN_ID}"
    slug_name_b = f"Race-Slug {RUN_ID}"

    def submit_colliding_slug(name):
        return client.post(
            "/catalog/items",
            headers=AUTH,
            json={"name": name, "slot": "top", "price": 10, "svg": GOOD_SVG},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        slug_responses = list(
            pool.map(submit_colliding_slug, [slug_name_a, slug_name_b])
        )
    slug_codes = sorted(r.status_code for r in slug_responses)
    results.append(
        (
            "concurrent slug collision: exactly one 201 and one 409",
            slug_codes == [201, 409],
            str(slug_codes),
        )
    )
    slug_winner = next((r for r in slug_responses if r.status_code == 201), None)
    if slug_winner is not None:
        won = slug_winner.json()
        created_item_ids.append(uuid.UUID(won["item_id"]))
        path = catalog_art.UPLOAD_DIR / won["image_url"].split("/media/uploads/", 1)[1]
        written_paths.append(path)
        results.append(("the winning file is intact, not corrupted", path.is_file() and "viewBox" in path.read_text(encoding="utf-8"), ""))
    slug_loser = next((r for r in slug_responses if r.status_code == 409), None)
    results.append(
        (
            "the loser's refusal explains the slug collision, not a generic 500",
            slug_loser is not None and "taken" in str(slug_loser.json().get("detail", "")).lower(),
            str(slug_loser.json().get("detail")) if slug_loser is not None else "no 409 in responses",
        )
    )

    # --- Patch: the art changes, the URL does not -------------------------
    redrawn = GOOD_SVG.replace("#E4002B", "#37C2A6")
    response = client.patch(
        f"/catalog/items/{item_id}", headers=AUTH, json={"svg": redrawn, "price": 200}
    )
    patched = response.json()
    results.append(("patch art and price -> 200", response.status_code == 200, str(response.status_code)))
    results.append(("price updated", patched.get("price") == 200, str(patched.get("price"))))
    results.append(
        (
            "url unchanged, so wardrobes pick up the new drawing",
            patched.get("image_url") == created["image_url"],
            str(patched.get("image_url")),
        )
    )
    results.append(("the file on disk was rewritten", "#37C2A6" in layer.read_text(encoding="utf-8"), ""))
    results.append(("the thumbnail was rewritten too", "#37C2A6" in thumb.read_text(encoding="utf-8"), ""))

    response = client.patch(f"/catalog/items/{item_id}", headers=AUTH, json={"svg": "<svg/>"})
    results.append(("patch with a bad drawing -> 422", response.status_code == 422, str(response.status_code)))
    results.append(("a refused patch leaves the good art in place", "#37C2A6" in layer.read_text(encoding="utf-8"), ""))

    # --- Delete safety ----------------------------------------------------
    with SessionLocal() as db:
        owner = User(username=f"catalog_{RUN_ID}", email=f"catalog_{RUN_ID}@example.com")
        db.add(owner)
        db.flush()
        created_user_ids.append(owner.user_id)
        db.add(UserWardrobe(user_id=owner.user_id, item_id=item_id))
        db.commit()

    response = client.delete(f"/catalog/items/{item_id}", headers=AUTH)
    results.append(("delete an owned item -> 409", response.status_code == 409, str(response.status_code)))
    results.append(("the owned item survives the refusal", layer.is_file(), ""))

    with SessionLocal() as db:
        db.execute(delete(UserWardrobe).where(UserWardrobe.item_id == item_id))
        db.commit()

    response = client.delete(f"/catalog/items/{item_id}", headers=AUTH)
    results.append(("delete an unowned item -> 204", response.status_code == 204, str(response.status_code)))
    if response.status_code == 204:
        created_item_ids.remove(item_id)
    results.append(("its files are gone with it", not layer.exists() and not thumb.exists(), ""))
    results.append(("deleting it again -> 404", client.delete(f"/catalog/items/{item_id}", headers=AUTH).status_code == 404, ""))

finally:
    settings.catalog_api_key = original_key
    cleanup()

failed = 0
for name, ok, extra in results:
    report(name, ok, extra)
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed.")
if failed:
    raise SystemExit(1)
