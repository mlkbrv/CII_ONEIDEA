"""
Generate redeemable codes for bottle caps.

    python scripts/generate_codes.py --count 20 --coins 50
    python scripts/generate_codes.py --count 5000 --coins 50 --product "Coca-Cola 0.5" --sku CC-05L --out codes.csv

Codes go into `qr_codes`, the same table POST /qr/redeem reads. Each is
redeemable exactly once, by one account, for its coin value.

## The alphabet

Codes are typed by hand off a wet cap, often by someone standing in a crowd.
So the alphabet excludes every pair that gets misread: no O or 0, no I, L or
1, no S or 5, no B or 8, no Z or 2. What is left is unambiguous in both upper
and lower case, and redemption folds case and strips whitespace anyway.

Grouping into blocks of four is not decoration — it is what makes a code
checkable at a glance and typable without losing your place.

## Collisions

`code` is UNIQUE, so a duplicate cannot be inserted. With this alphabet a
4+4 code is 22^8 ≈ 5.5e10 possibilities; at fest scale a collision is
vanishingly unlikely, and the insert is retried if one happens rather than
failing the batch.
"""
import argparse
import csv
import secrets
import sys

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models import Product, QRCode

# No O/0, I/L/1, S/5, B/8, Z/2 — see the module docstring.
ALPHABET = "ACDEFGHJKMNPQRTUVWXY34679"
BLOCK = 4
BLOCKS = 2


def make_code(prefix: str) -> str:
    body = "-".join(
        "".join(secrets.choice(ALPHABET) for _ in range(BLOCK)) for _ in range(BLOCKS)
    )
    return f"{prefix}-{body}" if prefix else body


def resolve_product(db, name: str, sku: str) -> Product:
    """Find the product by SKU, or create it.

    By SKU rather than by name: the name is a label that gets edited, the SKU
    is the identifier, and it is what carries the UNIQUE constraint.
    """
    product = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
    if product is None:
        product = Product(name=name, sku=sku)
        db.add(product)
        db.flush()
        print(f"Created product {name!r} (sku {sku})")
    return product


def generate(count: int, coins: int, product: Product, prefix: str, db) -> list[str]:
    created: list[str] = []
    attempts = 0

    while len(created) < count and attempts < count * 10:
        attempts += 1
        code = make_code(prefix)
        qr = QRCode(code=code, product_id=product.product_id, coin_value=coins)
        db.add(qr)
        try:
            # Flushed one at a time so a collision costs one retry rather than
            # rolling back the whole batch.
            db.flush()
        except IntegrityError:
            db.rollback()
            continue
        created.append(code)

    if len(created) < count:
        print(f"Only generated {len(created)} of {count} — too many collisions", file=sys.stderr)
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20, help="How many codes")
    parser.add_argument("--coins", type=int, default=50, help="Coins per code")
    parser.add_argument("--product", default="Coca-Cola 0.5", help="Product name")
    parser.add_argument("--sku", default="CC-05L", help="Product SKU (the identifier)")
    parser.add_argument("--prefix", default="CF", help="Code prefix, or '' for none")
    parser.add_argument("--out", help="Also write a CSV here, for printing")
    args = parser.parse_args()

    if args.coins <= 0:
        print("--coins must be positive (the DB enforces it too)", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        product = resolve_product(db, args.product, args.sku)
        codes = generate(args.count, args.coins, product, args.prefix, db)
        db.commit()

    for code in codes:
        print(code)

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["code", "coins", "product"])
            for code in codes:
                writer.writerow([code, args.coins, args.product])
        print(f"\nWrote {len(codes)} code(s) to {args.out}", file=sys.stderr)

    print(f"\n{len(codes)} code(s), {args.coins} coins each.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
