import asyncio

from app.bot.runner import run_polling


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
