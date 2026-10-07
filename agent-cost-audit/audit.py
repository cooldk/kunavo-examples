#!/usr/bin/env python3
"""Offline cost arithmetic for one tariff. Python 3.9+, standard library only."""
import argparse
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

BUCKETS = ("uncached_input", "cache_write", "cache_read", "output")


def audit(document):
    prices = {}
    for bucket in BUCKETS:
        try:
            price = Decimal(str(document["prices_usd_per_million"][bucket]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Missing or invalid price: {bucket}") from None
        if not price.is_finite() or price < 0:
            raise ValueError(f"Price must be finite and nonnegative: {bucket}")
        prices[bucket] = price
    tasks = document.get("tasks")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be an array")
    totals = {"work": Decimal(0), "healthcheck": Decimal(0)}
    result, seen, accepted, work_attempts = [], set(), 0, 0
    for task in tasks:
        task_id = task.get("id")
        if not isinstance(task_id, str) or not task_id or task_id in seen:
            raise ValueError("Task IDs must be unique nonempty strings")
        seen.add(task_id)
        kind = task.get("kind")
        if kind not in totals or type(task.get("accepted")) is not bool:
            raise ValueError(f"Invalid kind/accepted for {task_id}")
        if kind == "healthcheck" and task["accepted"]:
            raise ValueError("A healthcheck is not an accepted work task")
        attempts = task.get("attempts")
        if not isinstance(attempts, list) or not attempts:
            raise ValueError(f"At least one measured attempt is required: {task_id}")
        cost, inputs, reads = Decimal(0), 0, 0
        for attempt in attempts:
            for bucket in BUCKETS:
                tokens = attempt.get(bucket)
                if type(tokens) is not int or tokens < 0:
                    raise ValueError(f"Missing/noninteger/negative token count: {task_id}.{bucket}")
                cost += Decimal(tokens) * prices[bucket] / Decimal(1_000_000)
                if bucket != "output":
                    inputs += tokens
                if bucket == "cache_read":
                    reads += tokens
        totals[kind] += cost
        if kind == "work":
            work_attempts += len(attempts)
            accepted += int(task["accepted"])
        result.append({"id": task_id, "kind": kind, "attempts": len(attempts),
                       "accepted": task["accepted"], "estimated_usd": str(cost),
                       "cache_read_fraction_of_input": str(Decimal(reads) / inputs) if inputs else None})
    return {"tasks": result, "work_attempts": work_attempts, "accepted_work_tasks": accepted,
            "work_estimated_usd": str(totals["work"]),
            "healthcheck_estimated_usd": str(totals["healthcheck"]),
            "total_estimated_usd": str(sum(totals.values())),
            "work_cost_per_accepted_task_usd": str(totals["work"] / accepted) if accepted else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Normalized JSON with explicit rates and measured attempts")
    args = parser.parse_args()
    try:
        print(json.dumps(audit(json.loads(args.input.read_text(encoding="utf-8"))), indent=2))
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        parser.exit(2, f"Invalid input: {error}\n")


if __name__ == "__main__":
    main()
