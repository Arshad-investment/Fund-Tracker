"""Sanity checks for the site's data before publishing. Prints OK or a list of problems."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data" / "review.json"
SECTIONS = {"header", "summary", "today", "scenario", "scenario_chart", "otherrisks", "context",
            "funds", "dipbuy", "menu", "notes", "footer"}
problems = []


def bad(msg):
    problems.append(msg)


def check_runs(runs, where):
    if isinstance(runs, str):
        try:
            runs = json.loads(runs)
        except ValueError:
            bad(f"{where}: runs is not valid JSON")
            return
    if not isinstance(runs, list):
        bad(f"{where}: runs must be a list")
        return
    for r in runs:
        if not isinstance(r, dict) or not isinstance(r.get("text"), str):
            bad(f"{where}: every run needs a text string")
            continue
        href = r.get("href")
        if href is not None:
            m = re.fullmatch(r"#f(\d+)", href)
            if m:
                if not 1 <= int(m.group(1)) <= 28:
                    bad(f"{where}: fund link {href} out of range")
            elif not href.startswith(("https://", "http://", "#")):
                bad(f"{where}: odd link {href}")


try:
    blocks = json.loads(PATH.read_text(encoding="utf-8"))
except ValueError as e:
    print(f"review.json is not valid JSON: {e}")
    sys.exit(1)

if not isinstance(blocks, list) or not blocks:
    print("review.json must be a non-empty list")
    sys.exit(1)

seqs = [b.get("seq") for b in blocks]
if any(not isinstance(s, int) for s in seqs) or len(set(seqs)) != len(seqs):
    bad("seq values must be unique integers")

for b in blocks:
    where = f"seq {b.get('seq')} ({b.get('section')}/{b.get('kind')})"
    if b.get("section") not in SECTIONS:
        bad(f"{where}: unknown section")
    if not b.get("kind"):
        bad(f"{where}: missing kind")
    for key in ("runs", "label"):
        if key in b and b[key] is not None:
            check_runs(b[key], where)
    if "cells" in b and b["cells"] is not None:
        cells = b["cells"]
        if isinstance(cells, str):
            cells = json.loads(cells)
        for i, c in enumerate(cells):
            check_runs(c, f"{where} cell {i + 1}")

text = json.dumps(blocks, ensure_ascii=False)
funds_text = (ROOT / "data" / "funds.json").read_text(encoding="utf-8")
page_text = (ROOT / "index.html").read_text(encoding="utf-8")
# Names that must never appear (stored reversed so they are not spelled out in the repo).
BANNED = [w[::-1] for w in ("BDA", "CTJ", "knab tnempoleved naisa", "eenimon", "rotartsinimda nalp")]
for name, t in (("review.json", text), ("funds.json", funds_text), ("index.html", page_text)):
    for w in BANNED:
        if re.search(r"\b" + re.escape(w) + r"\b", t, re.I):
            bad(f"{name} contains a banned name")
    if re.search(r"\b(USD|EUR)[- ]?(based )?members?\b|\bplan's\b|\bplan portal\b|\bfund menu\b", t, re.I):
        bad(f"{name} uses plan/member/menu wording; present the 28 funds as a comprehensive list")
if "Fund it from" in text:
    bad('the "Fund it from" column is back')

today = sorted((b for b in blocks if b.get("section") == "today"), key=lambda b: b["seq"])
kinds = [b.get("kind") for b in today]
if kinds[:4] != ["eyebrow", "h2", "lead", "thead"]:
    bad(f"today must start eyebrow, h2, lead, thead (found {kinds[:4]})")
if kinds.count("tr") < 2:
    bad("today needs at least 2 table rows")
if "details" not in kinds:
    bad("today is missing the Earlier updates block")
elif kinds.count("dt") > 21:
    bad("more than 21 earlier updates; trim the oldest")
if today and not today[0]["runs"][0]["text"].startswith("Update · "):
    bad("today eyebrow must start 'Update · '")

if not any(b.get("section") == "header" and b.get("kind") == "meta"
           and "News updated" in json.dumps(b.get("runs"), ensure_ascii=False) for b in blocks):
    bad("header 'News updated' line is missing")

if problems:
    print("PROBLEMS:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("OK")
