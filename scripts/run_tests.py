"""
Run every test script in tests/ and summarise the result.

The suite inherited from PolarBear is a set of standalone scripts, not a
pytest suite: each one talks to a real PostgreSQL, prints "[PASS] ..." /
"[FAIL] ..." lines and cleans up after itself. That is worth keeping — the
value of these tests is that they exercise real row locks, real UNIQUE
constraints and real enum types, none of which a mocked session would catch.

What was missing was a way to run them all and get one answer. This does
that: each script runs in its own process (so one crash cannot take the run
down), and a script counts as failed if it exits non-zero or prints any
[FAIL] line.

    python scripts/run_tests.py           # everything
    python scripts/run_tests.py telegram  # only scripts matching "telegram"
"""
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT / "tests"

# Needs a live competition to expire, so it sleeps through a real interval.
SLOW = {"test_competition_expiration"}


def discover(pattern: str | None) -> list[str]:
    names = sorted(
        path.stem
        for path in TESTS_DIR.glob("test_*.py")
        if pattern is None or pattern in path.stem
    )
    # Run the slow ones last so quick failures surface immediately.
    return sorted(names, key=lambda name: (name in SLOW, name))


def run_one(name: str) -> tuple[bool, str]:
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-m", f"tests.{name}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = time.monotonic() - started
    output = result.stdout + result.stderr

    failures = [line for line in output.splitlines() if line.startswith("[FAIL]")]
    passes = [line for line in output.splitlines() if line.startswith("[PASS]")]
    ok = result.returncode == 0 and not failures

    summary = f"{len(passes)} passed, {len(failures)} failed, {elapsed:.1f}s"
    if not ok:
        detail = "\n".join(failures[:10]) or output.strip()[-2000:]
        summary = f"{summary}\n{detail}"
    return ok, summary


def main() -> int:
    pattern = sys.argv[1] if len(sys.argv) > 1 else None
    names = discover(pattern)
    if not names:
        print(f"No test scripts matched {pattern!r}")
        return 1

    print(f"Running {len(names)} test script(s)\n")
    failed: list[str] = []

    for name in names:
        ok, summary = run_one(name)
        print(f"[{'OK  ' if ok else 'FAIL'}] {name:34} {summary}")
        if not ok:
            failed.append(name)

    print()
    if failed:
        print(f"{len(failed)} of {len(names)} script(s) FAILED: {', '.join(failed)}")
        return 1
    print(f"All {len(names)} script(s) passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
