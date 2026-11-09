"""Checks that the price readers understand each site's format.

Run with:  python -m pytest tests   (or just: python tests/test_parsers.py)
The sample pages below are cut down from the real page layouts.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import update_prices as up  # noqa: E402
import update_history as uh  # noqa: E402

FIN_AT = """<html><nav><a>Nettoinventarwert</a></nav><div class="box"><h2>Nettoinventarwert (NAV)</h2>
<table><tr><td>40&nbsp;316,97 JPY</td><td>-0,14 JPY</td><td>0,00 %</td></tr>
<tr><td>Vortag</td><td>40 317,11 JPY</td><td>Datum</td><td>03.11.2026</td></tr></table></div></html>"""

FIN_CH = """<div><h2>Nettoinventarwert (NAV)</h2><table><tr><td>1’271.88 USD</td><td>-3.10 USD</td>
<td>-1.13 %</td></tr><tr><td>Vortag</td><td>274.98 USD</td><td>Datum</td><td>03.11.2026</td></tr></table></div>"""

ISHARES = """<table><tr><th>Investor Class</th><th>Currency</th><th>NAV</th></tr>
<tr><td>Class D</td><td>EUR</td><td>18.78</td><td>0.00</td><td>-0.02</td><td>04/Nov/2026</td><td>19.01</td><td>15.53</td><td>IE00BDRK7R97</td></tr>
<tr><td>Class D</td><td>USD</td><td>18.67</td><td>0.06</td><td>0.34</td><td>04/Nov/2026</td><td>19.57</td><td>15.81</td><td>IE00BD0NCP86</td></tr></table>"""

ISHARES_DE = """<table><tr><td>Klasse D</td><td>USD</td><td>30.25</td><td>0.44</td><td>1.47</td>
<td>20.Okt.2026</td><td>30.87</td><td>25.41</td><td>IE00BD0NCN62</td></tr></table>"""

FT = """<div class="mod-tearsheet-overview__quote"><ul><li><span>Price (USD)</span><span>166.82</span></li><li><span>Today's Change</span><span>0.58 / 0.35%</span></li></ul><div class="mod-disclaimer">Data delayed at least 15 minutes, as of Nov 04 2026.</div></div>"""

VANGUARD = """<div>Prices NAV Price (USD) <b>$200.93</b> USD Change +$0.53 0.27% As at Nov 05 2026 NAV 52-week high</div>"""


def test_numbers():
    assert up.to_number("40 316,97") == 40316.97
    assert up.to_number("1’234.56") == 1234.56
    assert up.to_number("1,234.56") == 1234.56
    assert up.to_number("-0,14") == -0.14


def test_dates():
    assert up.to_date("03.11.2026") == "2026-11-03"
    assert up.to_date("04/Nov/2026") == "2026-11-04"
    assert up.to_date("20.Okt.2026") == "2026-10-20"
    assert up.to_date("Nov 5, 2026") == "2026-11-05"


def test_finanzen_at():
    r = up.parse_finanzen(FIN_AT, {"currency": "JPY"})
    assert r == {"nav": 40316.97, "change_pct": 0.0, "nav_date": "2026-11-03"}


def test_finanzen_ch():
    r = up.parse_finanzen(FIN_CH, {"currency": "USD"})
    assert r == {"nav": 1271.88, "change_pct": -1.13, "nav_date": "2026-11-03"}


def test_finanzen_wrong_currency():
    try:
        up.parse_finanzen(FIN_CH, {"currency": "EUR"})
    except ValueError:
        return
    raise AssertionError("should refuse a page in another currency")


def test_ishares_picks_right_row():
    r = up.parse_ishares(ISHARES, {"currency": "USD", "isin": "IE00BD0NCP86"})
    assert r == {"nav": 18.67, "change_pct": 0.34, "nav_date": "2026-11-04"}


def test_ishares_german_month():
    r = up.parse_ishares(ISHARES_DE, {"currency": "USD", "isin": "IE00BD0NCN62"})
    assert r["nav_date"] == "2026-10-20" and r["nav"] == 30.25


def test_vanguard():
    r = up.parse_vanguard(VANGUARD, {"currency": "USD"})
    assert r == {"nav": 200.93, "change_pct": 0.27, "nav_date": "2026-11-05"}


def test_ft():
    r = up.parse_ft(FT, {"currency": "USD"})
    assert r == {"nav": 166.82, "change_pct": 0.35, "nav_date": "2026-11-04"}


def test_ft_history():
    page = '<section data-mod-config="{&quot;inception&quot;:&quot;2006&quot;,&quot;xid&quot;:&quot;536357519&quot;}"></section>'
    assert uh.find_xid(page) == "536357519"
    answer = '{"html":"<tr><td><span class=\\"a\\">Thursday, November 05, 2026</span><span>Thu, Nov 05, 2026</span></td><td>117.19</td><td>117.19</td><td>117.19</td><td>117.19</td><td>----</td></tr><tr><td><span>Wednesday, November 04, 2026</span></td><td>113.05</td><td>113.05</td><td>113.05</td><td>113.05</td><td>----</td></tr>"}'
    assert uh.parse_history(answer) == [("2026-11-05", 117.19), ("2026-11-04", 113.05)]


def test_misread_guard():
    try:
        up.check({"nav": 50.0, "nav_date": "2026-11-05"}, {"nav": 100.0, "nav_date": "2026-11-04"})
    except ValueError:
        return
    raise AssertionError("a 50% jump should be rejected")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
