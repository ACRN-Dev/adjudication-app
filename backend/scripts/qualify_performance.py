"""Repeatable read-only smoke/load/soak qualification with JSON evidence."""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx


PROFILES = {
    "smoke": {"duration": 15, "concurrency": 4},
    "load": {"duration": 300, "concurrency": 25},
    "soak": {"duration": 7200, "concurrency": 15},
}


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


async def run(args):
    profile = PROFILES[args.profile]
    duration = args.duration or profile["duration"]
    concurrency = args.concurrency or profile["concurrency"]
    endpoints = args.endpoint or ["/health/live", "/health/ready", "/api/auth/me"]
    limits = httpx.Limits(max_connections=concurrency + 5, max_keepalive_connections=concurrency)
    latencies: list[float] = []
    statuses, errors = Counter(), Counter()
    missing_correlation = completed = 0
    started = time.perf_counter()
    stop_at = started + duration
    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=args.request_timeout,
                                 limits=limits, verify=not args.insecure) as client:
        if args.email:
            response = await client.post("/api/auth/login", json={"email": args.email, "password": args.password})
            response.raise_for_status()
        lock = asyncio.Lock()

        async def worker(worker_id):
            nonlocal completed, missing_correlation
            index = worker_id
            while time.perf_counter() < stop_at:
                path = endpoints[index % len(endpoints)]
                index += 1
                before = time.perf_counter()
                try:
                    response = await client.get(path)
                    elapsed = (time.perf_counter() - before) * 1000
                    async with lock:
                        latencies.append(elapsed)
                        statuses[str(response.status_code)] += 1
                        completed += 1
                        if not response.headers.get("x-correlation-id"):
                            missing_correlation += 1
                        if response.status_code >= 500:
                            errors["server_5xx"] += 1
                        elif response.status_code >= 400:
                            errors["client_4xx"] += 1
                except Exception as exc:
                    async with lock:
                        completed += 1
                        errors[type(exc).__name__] += 1

        await asyncio.gather(*(worker(i) for i in range(concurrency)))

    elapsed = time.perf_counter() - started
    failures = sum(errors.values())
    error_rate = failures / max(completed, 1)
    evidence = {
        "schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": args.base_url, "profile": args.profile, "duration_seconds": round(elapsed, 3),
        "concurrency": concurrency, "endpoints": endpoints, "requests": completed,
        "throughput_rps": round(completed / max(elapsed, .001), 3), "status_counts": dict(statuses),
        "error_counts": dict(errors), "error_rate": round(error_rate, 6),
        "latency_ms": {"min": round(min(latencies), 3) if latencies else None,
                       "mean": round(statistics.fmean(latencies), 3) if latencies else None,
                       "p50": round(percentile(latencies, .50), 3), "p95": round(percentile(latencies, .95), 3),
                       "p99": round(percentile(latencies, .99), 3), "max": round(max(latencies), 3) if latencies else None},
        "missing_correlation_ids": missing_correlation,
        "thresholds": {"max_error_rate": args.max_error_rate, "max_p95_ms": args.max_p95_ms,
                       "min_throughput_rps": args.min_throughput_rps},
    }
    violations = []
    if error_rate > args.max_error_rate: violations.append("error_rate")
    if percentile(latencies, .95) > args.max_p95_ms: violations.append("p95_latency")
    if evidence["throughput_rps"] < args.min_throughput_rps: violations.append("throughput")
    if missing_correlation: violations.append("correlation_id")
    evidence["result"] = "PASS" if not violations else "FAIL"
    evidence["violations"] = violations
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if not violations else 1


def parser():
    p = argparse.ArgumentParser(description="Qualify read-only API performance and stability")
    p.add_argument("--base-url", required=True); p.add_argument("--profile", choices=PROFILES, default="smoke")
    p.add_argument("--duration", type=int); p.add_argument("--concurrency", type=int)
    p.add_argument("--endpoint", action="append", help="Read-only path; repeat for a mixed workload")
    p.add_argument("--email"); p.add_argument("--password", default="")
    p.add_argument("--request-timeout", type=float, default=15); p.add_argument("--max-error-rate", type=float, default=.01)
    p.add_argument("--max-p95-ms", type=float, default=1000); p.add_argument("--min-throughput-rps", type=float, default=1)
    p.add_argument("--insecure", action="store_true"); p.add_argument("--output", default="output/qualification/performance.json")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
