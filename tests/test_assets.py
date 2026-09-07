"""
Check that every clothing item's artwork actually exists and is servable.

Run from the project root:
    .venv/Scripts/python -m tests.test_assets

This is the test that would have caught the state this project was in: all 18
seeded items pointed at https://mycolabear.example.com, a domain that does not
exist, so the shop and every avatar rendered as broken images and nothing
failed anywhere. A catalogue row whose image_url leads nowhere is a bug, and
nothing else in the suite looks at it.

It also guards the layering contract: an outfit is rendered by stacking these
files, which only works while every one of them shares the avatar's viewBox.
Rename a slug in scripts/generate_assets.py without updating the migration, or
draw a layer on a different canvas, and this fails.

Touches no database rows and creates no users.
"""
import pathlib
import re
import warnings

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.main import app
from app.models import ClothingAvailability, ClothingItem

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

client = TestClient(app)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANVAS = "0 0 512 768"
SLOTS = ["hair", "hat", "top", "bottom", "shoes", "accessory"]


def report(name: str, ok: bool, extra: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({extra})" if extra else ""))


def view_box(path: pathlib.Path) -> str | None:
    match = re.search(r'viewBox="([^"]+)"', path.read_text(encoding="utf-8"))
    return match.group(1) if match else None


results = []

with SessionLocal() as db:
    items = db.execute(select(ClothingItem)).scalars().all()
    catalogue = [(item.name, item.image_url) for item in items]

results.append(("the catalogue is not empty", len(catalogue) > 0, f"{len(catalogue)} items"))

# --- 1. Every item points at a file that exists ----------------------------
missing = [name for name, url in catalogue if not (ROOT / url.lstrip("/")).is_file()]
results.append((
    "every item's image_url resolves to a file on disk",
    not missing,
    ", ".join(missing[:5]),
))

placeholders = [name for name, url in catalogue if "example.com" in url]
results.append((
    "no item still points at the placeholder domain",
    not placeholders,
    ", ".join(placeholders[:5]),
))

# --- 2. Every item has a shop thumbnail ------------------------------------
no_thumb = []
for name, url in catalogue:
    full = ROOT / url.lstrip("/")
    if not full.with_name(f"{full.stem}.thumb.svg").is_file():
        no_thumb.append(name)
results.append((
    "every item has a cropped shop thumbnail",
    not no_thumb,
    ", ".join(no_thumb[:5]),
))

# --- 3. The layering contract ---------------------------------------------
# Stacking only works because every full-size layer shares one canvas.
wrong_canvas = []
for name, url in catalogue:
    full = ROOT / url.lstrip("/")
    if full.is_file() and view_box(full) != CANVAS:
        wrong_canvas.append(f"{name}={view_box(full)}")
results.append((
    "every garment is drawn on the avatar's canvas",
    not wrong_canvas,
    ", ".join(wrong_canvas[:3]),
))

base_files = [ROOT / "media/avatar/base.svg", ROOT / "media/avatar/base-back.svg"]
results.append((
    "the avatar base layers exist and share that canvas",
    all(p.is_file() and view_box(p) == CANVAS for p in base_files),
    "",
))

thumbs_cropped = []
for name, url in catalogue:
    full = ROOT / url.lstrip("/")
    thumb = full.with_name(f"{full.stem}.thumb.svg")
    if thumb.is_file() and view_box(thumb) == CANVAS:
        thumbs_cropped.append(name)
results.append((
    "thumbnails are cropped rather than full-canvas copies",
    not thumbs_cropped,
    ", ".join(thumbs_cropped[:5]),
))

# --- 4. Coverage across slots ---------------------------------------------
by_slot: dict[str, list[str]] = {}
buyable: dict[str, list[str]] = {}
with SessionLocal() as db:
    for item in db.execute(select(ClothingItem)).scalars().all():
        slot = item.category.slot.value
        by_slot.setdefault(slot, []).append(item.name)
        if item.availability_status == ClothingAvailability.AVAILABLE:
            buyable.setdefault(slot, []).append(item.name)

results.append((
    "every avatar slot has something to wear",
    all(by_slot.get(slot) for slot in SLOTS),
    str({slot: len(by_slot.get(slot, [])) for slot in SLOTS}),
))
results.append((
    "every slot has at least one AVAILABLE item to buy",
    all(buyable.get(slot) for slot in SLOTS),
    str({slot: len(buyable.get(slot, [])) for slot in SLOTS}),
))

# --- 5. The API actually serves them ---------------------------------------
sample = catalogue[0][1] if catalogue else "/media/avatar/base.svg"
response = client.get(sample)
results.append((
    "the API serves artwork from /media",
    response.status_code == 200 and response.text.lstrip().startswith("<svg"),
    f"{response.status_code} {sample}",
))
results.append((
    "and it is served as SVG, not downloaded as a blob",
    "svg" in response.headers.get("content-type", ""),
    response.headers.get("content-type", ""),
))
results.append((
    "a path outside the media directory is not served",
    client.get("/media/../app/core/config.py").status_code != 200,
    "",
))


failed = 0
for name, ok, extra in results:
    report(name, ok, extra)
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed.")
if failed:
    raise SystemExit(1)
