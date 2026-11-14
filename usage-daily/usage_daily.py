"""One key, one daily usage snapshot. Python 3.9+, standard library only."""
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, Inexact, localcontext
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def previous_week(now=None):
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError("now must include a timezone")
    end = now.astimezone(timezone.utc).date() - timedelta(days=1)
    return end - timedelta(days=6), end


def daily_rows(payload, start, end):
    if (payload.get("bucket"), payload.get("start_date"),
            payload.get("end_date")) != ("day", str(start), str(end)):
        raise ValueError("unexpected bucket or reporting window")
    by_day = {}
    for row in payload["data"]:
        stamp = datetime.fromisoformat(row["bucket_start"].replace("Z", "+00:00"))
        if stamp.utcoffset() is None:
            raise ValueError("bucket_start must include a timezone")
        stamp = stamp.astimezone(timezone.utc)
        day = stamp.date()
        if stamp.time().isoformat() != "00:00:00" or not start <= day <= end:
            raise ValueError("unexpected daily bucket")
        if "model" in row or day in by_day:
            raise ValueError("expected one ungrouped row per day")
        if not isinstance(row["cost_usd"], str):
            raise ValueError("cost_usd must be a decimal string")
        cost = Decimal(row["cost_usd"])
        if not cost.is_finite():
            raise ValueError("cost_usd must be finite")
        by_day[day] = cost
    return [(start + timedelta(days=i),
             by_day.get(start + timedelta(days=i), Decimal("0")))
            for i in range((end - start).days + 1)]


def main():
    if len(sys.argv) == 2:  # Offline fixture; no key or network required.
        with open(sys.argv[1], encoding="utf-8") as handle:
            payload = json.load(handle)
        start, end = (date.fromisoformat(payload[k])
                      for k in ("start_date", "end_date"))
    else:
        start, end = previous_week()
        query = urlencode({"start_date": str(start), "end_date": str(end),
                           "bucket": "day"})
        request = Request("https://api.kunavo.com/v1/usage?" + query,
                          headers={"Authorization": "Bearer " + os.environ["KUNAVO_API_KEY"]})
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    rows = daily_rows(payload, start, end)
    with localcontext() as ctx:
        ctx.traps[Inexact] = True
        total = sum((cost for _, cost in rows), Decimal("0"))
    writer = csv.writer(sys.stdout)
    writer.writerow(["date_utc", "cost_usd"])
    writer.writerows((str(day), format(cost, "f")) for day, cost in rows)
    print("total_usd=" + format(total, "f"), file=sys.stderr)


if __name__ == "__main__":
    main()
