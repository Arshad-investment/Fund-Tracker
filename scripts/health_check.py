"""Daily health check. Prints OK, or the problems found (exit code 1).

Checks that prices were refreshed recently and that no fund's price is unusually old.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
store = json.loads((ROOT / "data" / "prices.json").read_text(encoding="utf-8"))
problems = []

updated = datetime.strptime(store["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
age_h = (datetime.now(timezone.utc) - updated).total_seconds() / 3600
if age_h > 9:
    problems.append(f"STALE_RUN: prices were last checked {age_h:.0f} hours ago (expected every 5-7 hours)")


def business_days_since(d):
    n, day = 0, d
    while day < date.today():
        day += timedelta(days=1)
        if day.weekday() < 5:
            n += 1
    return n


for no, p in sorted(store["prices"].items(), key=lambda kv: int(kv[0])):
    if not p.get("ok"):
        problems.append(f"SOURCE_FAIL: fund {no}: {str(p.get('error'))[:120]}")
    lag = business_days_since(date.fromisoformat(p["nav_date"]))
    if lag > 4:
        problems.append(f"OLD_PRICE: fund {no} price is dated {p['nav_date']} ({lag} business days old)")

if problems:
    print("\n".join(problems))
    sys.exit(1)
print("OK")
