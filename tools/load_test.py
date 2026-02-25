"""Simple HTTP load test (no external deps)."""

import argparse
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import build_opener, ProxyHandler


def fetch(url: str, timeout: float) -> float:
    start = time.perf_counter()
    opener = build_opener(ProxyHandler({}))
    with opener.open(url, timeout=timeout) as resp:
        resp.read()
    return time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()

    durations = []
    errors = 0
    first_error = None
    start_all = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [pool.submit(fetch, args.url, args.timeout) for _ in range(args.requests)]
        for fut in as_completed(futures):
            try:
                durations.append(fut.result())
            except Exception as exc:
                errors += 1
                if first_error is None:
                    first_error = exc

    total = time.perf_counter() - start_all
    if durations:
        durations_sorted = sorted(durations)
        p50 = durations_sorted[int(0.50 * (len(durations_sorted) - 1))]
        p90 = durations_sorted[int(0.90 * (len(durations_sorted) - 1))]
        p95 = durations_sorted[int(0.95 * (len(durations_sorted) - 1))]
        p99 = durations_sorted[int(0.99 * (len(durations_sorted) - 1))]
        print(f"requests: {args.requests}")
        print(f"concurrency: {args.concurrency}")
        print(f"errors: {errors}")
        print(f"total_time_s: {total:.3f}")
        print(f"rps: {len(durations) / total:.2f}")
        print(f"min_ms: {min(durations)*1000:.2f}")
        print(f"avg_ms: {statistics.mean(durations)*1000:.2f}")
        print(f"p50_ms: {p50*1000:.2f}")
        print(f"p90_ms: {p90*1000:.2f}")
        print(f"p95_ms: {p95*1000:.2f}")
        print(f"p99_ms: {p99*1000:.2f}")
    else:
        print("No successful requests.")
        if first_error is not None:
            print(f"first_error: {first_error}")


if __name__ == "__main__":
    main()
