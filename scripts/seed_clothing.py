"""Draw clothing for the catalog and put it in the shop.

    python scripts/seed_clothing.py --export OUT_DIR   # SVGs + preview.html, no database
    python scripts/seed_clothing.py --apply            # inside the API container

--apply does three things, in this order:
  1. repairs items whose art file is missing on disk, when this file has a
     drawing for that item's name (the file is written under the item's
     existing slug, so the URL and every wardrobe holding it stay valid);
  2. adds the new items below that are not in the shop yet;
  3. sets every item whose art file is still missing to "unavailable", so the
     shop never shows an empty picture.
It never overwrites a file that exists and never changes an existing price.

APP_ROOT=<path to the API source> lets --export run from another checkout.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

from clothing_art_base import svg
from clothing_art_fun import FUN_ACCESSORIES, FUN_BOTTOMS, FUN_HATS, FUN_SHOES, FUN_TOPS
from clothing_art_work import ACCESSORIES, BOTTOMS, HAIR, HATS, SHOES, TOPS

HATS.update(FUN_HATS)
TOPS.update(FUN_TOPS)
BOTTOMS.update(FUN_BOTTOMS)
SHOES.update(FUN_SHOES)
ACCESSORIES.update(FUN_ACCESSORIES)

CATEGORIES = {"hat": HATS, "top": TOPS, "bottom": BOTTOMS, "shoes": SHOES, "accessory": ACCESSORIES, "hair": HAIR}


def items():
    for slot, table in CATEGORIES.items():
        for name, (price, description, parts) in table.items():
            yield {"name": name, "slot": slot, "price": price, "description": description, "svg": svg(*parts)}


def export(out: pathlib.Path, root: pathlib.Path) -> None:
    from app.services import catalog_art

    out.mkdir(parents=True, exist_ok=True)
    base = (root / "media" / "avatar" / "base.svg").read_text(encoding="utf-8")
    cards = []
    for item in items():
        catalog_art.validate(item["svg"])
        slug = catalog_art.slugify(item["name"])
        (out / f"{item['slot']}-{slug}.svg").write_text(item["svg"], encoding="utf-8")
        cards.append(
            f'<figure><div class="bear">{base}<div class="layer">{item["svg"]}</div></div>'
            f'<figcaption>{item["name"]}<br><small>{item["slot"]} · {item["price"]}</small></figcaption></figure>'
        )
    html = (
        "<!doctype html><meta charset=utf-8><title>preview</title><style>"
        "body{font:14px sans-serif;background:#e8eef5;margin:12px}main{display:grid;grid-template-columns:repeat(auto-fill,170px);gap:10px}"
        "figure{margin:0;background:#fff;border-radius:10px;padding:6px;text-align:center}"
        ".bear{position:relative;width:150px;height:225px;margin:auto}.bear svg{width:150px;height:225px;display:block}"
        ".layer{position:absolute;inset:0}</style><main>" + "".join(cards) + "</main>"
    )
    (out / "preview.html").write_text(html, encoding="utf-8")
    print(f"{len(cards)} items -> {out}")


def apply() -> None:
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.models import AvatarSlot, ClothingAvailability, ClothingCategory, ClothingItem
    from app.services import catalog_art

    db = SessionLocal()
    repaired = created = hidden = 0
    try:
        existing = {i.name.lower(): i for i in db.execute(select(ClothingItem)).scalars().all()}
        taken_slugs = {
            (i.image_url.split("/")[-2], i.image_url.split("/")[-1][:-4])
            for i in existing.values() if i.image_url.startswith(catalog_art.UPLOAD_URL_PREFIX)
        }
        for entry in items():
            catalog_art.validate(entry["svg"])
            current = existing.get(entry["name"].lower())
            if current is not None:
                if current.image_url.startswith(catalog_art.UPLOAD_URL_PREFIX):
                    file = catalog_art.MEDIA_DIR / current.image_url.removeprefix("/media/")
                    if not file.exists():
                        slot, slug = current.image_url.split("/")[-2], current.image_url.split("/")[-1][:-4]
                        catalog_art.write(slot, slug, entry["svg"], overwrite=True)
                        repaired += 1
                continue
            category = db.execute(
                select(ClothingCategory).where(ClothingCategory.slot == AvatarSlot(entry["slot"])).order_by(ClothingCategory.category_id)
            ).scalars().first()
            if category is None:
                continue
            slug = catalog_art.slugify(entry["name"])
            while (entry["slot"], slug) in taken_slugs:
                slug += "-2"
            taken_slugs.add((entry["slot"], slug))
            url = catalog_art.write(entry["slot"], slug, entry["svg"], overwrite=False)
            db.add(ClothingItem(name=entry["name"], description=entry["description"], category_id=category.category_id,
                                price=entry["price"], image_url=url, availability_status=ClothingAvailability.AVAILABLE))
            created += 1
        db.flush()
        for item in db.execute(select(ClothingItem)).scalars().all():
            if item.image_url.startswith("/media/"):
                file = catalog_art.MEDIA_DIR / item.image_url.removeprefix("/media/")
                if not file.exists() and item.availability_status == ClothingAvailability.AVAILABLE:
                    item.availability_status = ClothingAvailability.UNAVAILABLE
                    hidden += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"repaired={repaired} created={created} hidden={hidden}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", type=pathlib.Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(os.environ.get("APP_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
    sys.path.insert(0, str(root))
    if args.export:
        export(args.export, root)
    elif args.apply:
        apply()
    else:
        parser.print_help()
