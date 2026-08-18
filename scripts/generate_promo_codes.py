import argparse
import asyncio
import csv
from datetime import datetime
from pathlib import Path

from app.core.database import async_session_maker
from app.services.promo import create_promo_code_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a batch of unique festival promo codes.")
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--coin-reward", type=int, default=50)
    parser.add_argument("--code-length", type=int, default=10)
    parser.add_argument("--expires-at", type=str, default=None)
    parser.add_argument("--output", type=Path, default=Path("promo_codes.csv"))
    return parser.parse_args()


def parse_expires_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("expires-at must include a timezone, e.g. 2026-09-30T23:59:59+00:00")
    return parsed


async def run(args: argparse.Namespace) -> None:
    expires_at = parse_expires_at(args.expires_at)
    async with async_session_maker() as session:
        codes = await create_promo_code_batch(
            session,
            count=args.count,
            coin_reward=args.coin_reward,
            expires_at=expires_at,
            code_length=args.code_length,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["code", "coin_reward", "expires_at"])
        expires_value = expires_at.isoformat() if expires_at else ""
        for code in codes:
            writer.writerow([code, args.coin_reward, expires_value])
    print(f"Wrote {len(codes)} plaintext codes to {args.output}")
    print("Keep this file private. Only SHA-256 hashes were stored in the database.")


def main() -> None:
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
