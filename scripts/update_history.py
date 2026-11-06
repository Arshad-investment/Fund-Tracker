"""Fill data/history.csv with up to a year of daily prices per fund, from the Financial Times.

Run by the GitHub Action after update_prices.py. It keeps every row already in the file
and adds any dates it is missing, so a failed run never loses history.

How it works
- Each fund's FT tearsheet (markets.ft.com/data/funds/tearsheet/summary?s=ISIN:CCY)
  carries an internal id ("xid").
- FT's historical-prices endpoint returns a table of daily prices for that id.
"""

from __future__ import annotations

import csv
import html
import json
import re
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUNDS = ROOT / "data" / "funds.json"
HISTORY = ROOT / "data" / "history.csv"
DAYS = 380
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
    "Accept-Language": "en-GB,en;q=0.9",
}


def find_xid(tearsheet_html: str) -> str:
    text = html.unescape(tearsheet_html)
    m = re.search(r'"xid"\s*:\s*"?(\d+)', text) or re.search(r"data-mod-xid=\"?(\d+)", text)
    if not m:
        raise ValueError("FT id (xid) not found on the tearsheet")
    return m.group(1)


def parse_history(answer: str) -> list[tuple[str, float]]:
    """Read FT's historical-prices answer: JSON holding an HTML table of rows
    (Date | Open | High | Low | Close | Volume). Returns [(YYYY-MM-DD, close)]."""
    try:
        data = json.loads(answer)
        table = data.get("html") or (data.get("data") or {}).get("html") or ""
    except (ValueError, AttributeError):
        table = answer
    rows = []
    for tr in re.findall(r"(?is)<tr\b.*?</tr>", table):
        cells = [html.unescape(re.sub(r"(?s)<[^>]+>", " ", c)).strip()
                 for c in re.findall(r"(?is)<td\b[^>]*>(.*?)</td>", tr)]
        if len(cells) < 2:
            continue
        m = re.search(r"([A-Z][a-z]+) (\d{1,2}), (\d{4})", cells[0])
        if not m:
            continue
        try:
            day = datetime.strptime(" ".join(m.groups()), "%B %d %Y").date().isoformat()
        except ValueError:
            day = datetime.strptime(" ".join(m.groups()), "%b %d %Y").date().isoformat()
        nums = []
        for c in cells[1:5]:
            c = c.replace(",", "").split()[0] if c.split() else ""
            try:
                nums.append(float(c))
            except ValueError:
                pass
        if nums:
            rows.append((day, nums[-1]))  # the close, or the last price shown
    return rows


def main() -> int:
    import requests

    funds = json.loads(FUNDS.read_text(encoding="utf-8"))["funds"]
    existing: dict[tuple[str, int], list] = {}
    if HISTORY.exists():
        with HISTORY.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[(r["date"], int(r["no"]))] = [r["date"], int(r["no"]), r["isin"], r["nav"], r["currency"]]
    end = date.today()
    start = end - timedelta(days=DAYS)
    report = []
    for fund in funds:
        if fund.get("price_type") != "auto" or not fund.get("isin"):
            continue
        sym = f"{fund['isin']}:{fund['currency']}"
        try:
            page = requests.get(f"https://markets.ft.com/data/funds/tearsheet/summary?s={sym}", headers=HEADERS, timeout=30)
            page.raise_for_status()
            xid = find_xid(page.text)
            time.sleep(1)
            r = requests.get(
                "https://markets.ft.com/data/equities/ajax/get-historical-prices",
                params={"startDate": start.strftime("%Y/%m/%d"), "endDate": end.strftime("%Y/%m/%d"), "symbol": xid},
                headers={**HEADERS, "X-Requested-With": "XMLHttpRequest"}, timeout=30,
            )
            r.raise_for_status()
            rows = parse_history(r.text)
            if not rows:
                raise ValueError("no price rows in FT's answer: " + r.text[:120].replace("\n", " "))
            added = 0
            for day, nav in rows:
                key = (day, fund["no"])
                if key not in existing:
                    existing[key] = [day, fund["no"], fund["isin"], nav, fund["currency"]]
                    added += 1
            report.append(f"OK    {fund['no']:>2} {fund['fund'][:46]:<46} {len(rows):>4} days from FT, {added} new")
        except Exception as e:  # noqa: BLE001
            report.append(f"FAIL  {fund['no']:>2} {fund['fund'][:46]:<46} {e}")
        time.sleep(1)
    with HISTORY.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "no", "isin", "nav", "currency"])
        w.writerows(sorted(existing.values(), key=lambda r: (r[1], r[0])))
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
