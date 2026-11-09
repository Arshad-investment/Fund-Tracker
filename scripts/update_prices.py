"""Fetch the latest NAV for each fund and save it to data/prices.json.

Run by the GitHub Action every weekday. You can also run it yourself:
    pip install requests
    python scripts/update_prices.py

How it works
- data/funds.json lists each fund and one or more price pages ("sources").
- For each fund it tries the sources in order and keeps the first price it can read.
- If every source fails, the last good price is kept and the fund is marked as
  not updated, so the website never goes blank.
- A new NAV date is appended to data/history.csv, which builds a price history.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FUNDS = ROOT / "data" / "funds.json"
PRICES = ROOT / "data" / "prices.json"
HISTORY = ROOT / "data" / "history.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9,de;q=0.8",
}

# A new price more than this far from the last one is treated as a misread.
MAX_JUMP = 0.25

MONTHS = {
    "jan": 1, "jän": 1, "feb": 2, "mar": 3, "mär": 3, "apr": 4, "may": 5, "mai": 5,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "okt": 10, "nov": 11,
    "dec": 12, "dez": 12,
}


# ---------------------------------------------------------------- helpers

def page_text(raw_html: str) -> str:
    """Turn a web page into plain text, one space between words."""
    raw_html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?s)<[^>]+>", " ", raw_html)
    text = html.unescape(text).replace("\xa0", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", text)


def to_number(s: str) -> float:
    """Read '1 234,56', '1’234.56', '1,234.56' or '-0,14' as a float."""
    s = s.strip().replace(" ", "").replace("’", "").replace("'", "")
    s = s.replace("−", "-")  # unicode minus
    if "," in s and "." in s:
        # whichever comes last is the decimal mark
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def to_date(s: str) -> str:
    """Read '04.11.2026', '04/Nov/2026', '04.Nov.2026', '20.Okt.2026', 'Nov 5, 2026'
    or 'November 5, 2026' and return '2026-11-04'."""
    s = s.strip()
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        d, mo, y = map(int, m.groups())
        return date(y, mo, d).isoformat()
    m = re.fullmatch(r"(\d{1,2})[./\-\s]?([A-Za-zäÄ]{3,9})\.?[./\-\s]?(\d{4})", s)
    if m:
        d, mon, y = m.groups()
        return date(int(y), MONTHS[mon[:3].lower()], int(d)).isoformat()
    m = re.fullmatch(r"([A-Za-z]{3,9})\.? (\d{1,2}),? (\d{4})", s)
    if m:
        mon, d, y = m.groups()
        return date(int(y), MONTHS[mon[:3].lower()], int(d)).isoformat()
    raise ValueError(f"unknown date format: {s!r}")


NUM = r"-?\d[\d  ’'.,]*"
DATE_DMY = r"\d{1,2}[./\-]?\s?(?:[A-Za-zäÄ]{3,9}|\d{1,2})\.?[./\-]?\s?\d{4}"


# ---------------------------------------------------------------- parsers
# Each parser gets the page HTML and the fund, and returns
# {"nav": float, "change_pct": float | None, "nav_date": "YYYY-MM-DD"} or raises.

def parse_finanzen(raw_html: str, fund: dict) -> dict:
    """finanzen.at / finanzen.ch / finanzen.net fund pages.

    The page has a box like:
      Nettoinventarwert (NAV)  107,22 EUR 0,02 EUR 0,02 %  Vortag 107,21 EUR  Datum 31.07.2026
    """
    text = page_text(raw_html)
    starts = [m.start() for m in re.finditer("Nettoinventarwert", text)]
    if not starts:
        raise ValueError("no 'Nettoinventarwert (NAV)' box on the page")
    for i in starts:  # the word can also appear in menus; use the first box that parses
        box = text[i:i + 400]
        m = re.search(rf"({NUM})\s*([A-Z]{{3}})\s+({NUM})\s*[A-Z]{{3}}\s+({NUM})\s*%", box)
        d = re.search(r"Datum\s*(\d{1,2}\.\d{1,2}\.\d{4})", box)
        if not (m and d):
            continue
        nav, ccy, _chg, pct = m.groups()
        if ccy != fund["currency"]:
            raise ValueError(f"page currency {ccy} is not the fund's {fund['currency']}")
        return {"nav": to_number(nav), "change_pct": to_number(pct), "nav_date": to_date(d.group(1))}
    raise ValueError("NAV numbers or date not found in the NAV box")


def parse_ishares(raw_html: str, fund: dict) -> dict:
    """iShares / BlackRock product pages: the 'Pricing & Exchange' table.

    Each row reads like:  Class D | USD | 18.67 | 0.06 | 0.34 | 04/Nov/2026 | 19.57 | 15.81 | IE00BD0NCP86
    We find the row that holds this fund's ISIN.
    """
    isin = fund["isin"]
    for row in re.findall(r"(?is)<tr\b.*?</tr>", raw_html):
        if isin not in row:
            continue
        cells = [page_text(c).strip() for c in re.findall(r"(?is)<t[dh]\b[^>]*>(.*?)</t[dh]>", row)]
        cells = [c for c in cells if c]
        try:
            k = next(i for i, c in enumerate(cells) if c == fund["currency"])
        except StopIteration:
            continue
        nav, _chg, pct = cells[k + 1], cells[k + 2], cells[k + 3]
        when = next((c for c in cells[k + 4:] if re.fullmatch(DATE_DMY, c)), None)
        if when is None:
            continue
        return {"nav": to_number(nav), "change_pct": to_number(pct.rstrip("%")), "nav_date": to_date(when)}
    # Some pages render the table as plain text: fall back to a text search.
    text = page_text(raw_html)
    m = re.search(
        rf"{re.escape(fund['currency'])}\s+({NUM})\s+({NUM})\s+({NUM})%?\s+({DATE_DMY})"
        rf"\s+{NUM}\s+{NUM}\s+{re.escape(isin)}",
        text,
    )
    if m:
        nav, _chg, pct, when = m.groups()
        return {"nav": to_number(nav), "change_pct": to_number(pct), "nav_date": to_date(when)}
    raise ValueError(f"no pricing row for {isin}")


def parse_vanguard(raw_html: str, fund: dict) -> dict:
    """Vanguard fund pages: 'NAV Price (USD) $200.93 ... Change +$0.53 0.27% As at Nov 05 2026'."""
    text = page_text(raw_html)
    m = re.search(
        r"NAV Price \(\w{3}\)\s*\D{0,3}?([\d,]+\.\d+).{0,80}?([+\-−]?[\d.]+)%\s*(?:As at|At closure)\s*"
        r"([A-Za-z]{3,9}\.? \d{1,2},? \d{4}|\d{1,2} [A-Za-z]{3,9}\.? \d{4})",
        text,
    )
    if not m:
        raise ValueError("NAV price not found (the page may build it with JavaScript)")
    nav, pct, when = m.groups()
    when = when.replace(",", "")
    parts = when.split()
    when = f"{parts[0]} {parts[1]}, {parts[2]}" if parts[0][0].isalpha() else f"{parts[0]} {parts[1]} {parts[2]}"
    return {"nav": to_number(nav), "change_pct": to_number(pct), "nav_date": to_date(when)}


def parse_ft(raw_html: str, fund: dict) -> dict:
    """Financial Times fund tearsheets (markets.ft.com/data/funds/tearsheet/summary?s=ISIN:CCY).

    The quote bar reads like:  Price (USD) 166.82  Today's Change 0.58 / 0.35%  ...  as of Nov 04 2026
    """
    text = page_text(raw_html)
    m = re.search(r"Price \((\w{3})\)\s*([\d,]+\.\d+)", text)
    if not m:
        raise ValueError("price not found on the FT page")
    ccy, nav = m.groups()
    if ccy != fund["currency"]:
        raise ValueError(f"page currency {ccy} is not the fund's {fund['currency']}")
    c = re.search(r"Today.s Change\s*([+\-\u2212]?[\d.,]+)\s*/\s*([+\-\u2212]?[\d.,]+)%", text)
    d = re.search(r"as of ([A-Z][a-z]{2} \d{1,2},? \d{4})", text)
    if not d:
        raise ValueError("price date not found on the FT page")
    return {"nav": to_number(nav), "change_pct": to_number(c.group(2)) if c else None, "nav_date": to_date(d.group(1))}


PARSERS = {"finanzen": parse_finanzen, "ishares": parse_ishares, "vanguard": parse_vanguard, "ft": parse_ft}


# ---------------------------------------------------------------- main

def fetch(url: str) -> str:
    import requests  # imported here so the tests can run without it

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def check(new: dict, old: dict | None) -> None:
    if not new["nav"] or new["nav"] <= 0:
        raise ValueError("NAV is not a positive number")
    if old and old.get("nav"):
        jump = abs(new["nav"] / old["nav"] - 1)
        if jump > MAX_JUMP:
            raise ValueError(f"NAV moved {jump:.0%} since the last price; looks like a misread")
        if old.get("nav_date") and new["nav_date"] < old["nav_date"]:
            raise ValueError(f"page shows an older NAV date ({new['nav_date']})")


def update(fetcher=fetch, pause: float = 1.5) -> list[str]:
    funds = json.loads(FUNDS.read_text(encoding="utf-8"))["funds"]
    store = json.loads(PRICES.read_text(encoding="utf-8")) if PRICES.exists() else {"prices": {}}
    prices = store.setdefault("prices", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report, new_history = [], []

    for fund in funds:
        if fund.get("price_type") != "auto":
            continue
        key, old = str(fund["no"]), prices.get(str(fund["no"]))
        errors = []
        for src in fund.get("sources", []):
            try:
                result = PARSERS[src["parser"]](fetcher(src["url"]), fund)
                check(result, old)
            except Exception as e:  # noqa: BLE001 - any failure moves on to the next source
                errors.append(f"{src['parser']}: {e}")
                continue
            finally:
                time.sleep(pause)
            is_new = not old or result["nav_date"] != old.get("nav_date")
            prices[key] = {**result, "source_url": src["url"], "checked_at": now, "ok": True, "error": None}
            if is_new:
                new_history.append([result["nav_date"], fund["no"], fund["isin"], result["nav"], fund["currency"]])
            report.append(f"OK    {fund['no']:>2} {fund['fund'][:48]:<48} {result['nav']:>12,.2f} {result['nav_date']}"
                          + ("" if is_new else "  (no new NAV yet)"))
            break
        else:
            msg = "; ".join(errors) or "no sources listed"
            if old:
                old.update(ok=False, error=msg, checked_at=now)
            report.append(f"FAIL  {fund['no']:>2} {fund['fund'][:48]:<48} kept last price  <- {msg}")

    store["updated_at"] = now
    PRICES.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if new_history:
        with HISTORY.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(new_history)
    return report


if __name__ == "__main__":
    lines = update()
    out = "\n".join(lines)
    print(out)
    ok = sum(l.startswith("OK") for l in lines)
    summary = f"### Price update\n\n{ok} of {len(lines)} funds read.\n\n```\n{out}\n```\n"
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(summary)
    sys.exit(0)  # a partial failure still publishes the prices that did update
