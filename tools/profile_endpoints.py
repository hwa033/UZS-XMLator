"""Profile Flask endpoints using test_client (no external deps)."""

import argparse
import cProfile
import pstats
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web.app import app


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()

    client = app.test_client()

    def run_requests() -> None:
        for _ in range(args.iterations):
            client.get("/health")
            client.get("/ready")
            client.get("/")

    profiler = cProfile.Profile()
    start = time.perf_counter()
    profiler.enable()
    run_requests()
    profiler.disable()
    total = time.perf_counter() - start

    print(f"iterations: {args.iterations}")
    print(f"total_time_s: {total:.3f}")
    stats = pstats.Stats(profiler)
    stats.sort_stats("cumtime").print_stats(25)


if __name__ == "__main__":
    main()
