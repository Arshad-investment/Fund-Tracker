# Daily news update: instructions for Claude

A scheduled task runs these steps every morning so the site's news is current by about 6 am Manila.
Prices are handled separately by the GitHub Action in `.github/workflows/update.yml` (5:40 am, 12:40 pm, 6:40 pm and 11:40 pm Manila).
The site is live at https://arshad-investment.github.io/Fund-Tracker/. Every push to `main` republishes it automatically.

## 1. Get the repo

- Use an existing clone if there is one (`/home/claude/gh-fund-tracker`). Otherwise call `add_repo`
  (owner `Arshad-investment`, repo `Fund-Tracker`, access `push`), clone it as the tool says, and work there.
- Run `git pull --rebase` first. The price bot commits every morning.
- `gh` works only with REST: always pass `-R Arshad-investment/Fund-Tracker` (and `--ref main` for `gh workflow run`).

## 2. See what is already covered

Open `data/review.json` (a list of blocks; see "File format" below). The `today` section's first block is the
eyebrow, e.g. `Update · Mon 9 Nov 2026, 7 am Manila (covers Fri 6 Nov and the weekend)`. Research everything since then.

## 3. Research

Use WebSearch (standard mode; send independent searches in the same turn) and WebFetch for detail. Cover:

- US close: S&P 500, Nasdaq, Dow, chip index (SOX), NVIDIA and other AI names; AI-bubble signals; big-tech/AI earnings.
- Central banks: Fed (rate-hike odds, speeches, minutes), BoJ, ECB, BoE, RBA. US data releases (CPI, jobs, GDP).
- Bond yields: US 2- and 10-year, gilts, JGBs, French spread.
- Oil, Iran and the Strait of Hormuz; OPEC+.
- Currencies: yen (intervention watch near 160), euro, Asian currencies.
- Gold. Asia: Nikkei, KOSPI, Taiwan, Hang Seng, ASX. Taiwan/China tension. AI-related credit stress.
- Anything specific to the 28 funds below.

Weekends: the Saturday run covers Friday's US close; the Sunday run is short (weekend news and the week ahead);
the Monday run covers the weekend and the week ahead. Always post an update, even a short one, so the date stays fresh.

Use only figures you retrieved in this run. If sources disagree, give a range or say so. Never guess a number.

## 4. Edit `data/review.json`

Edit with a Python script: `json.load`, change the blocks, renumber `seq` 1..N in list order, then
`json.dump(blocks, f, ensure_ascii=False, indent=0)`.

### Today tab (`section: "today"`), in this order

1. `eyebrow`: `Update · <Ddd D Mon YYYY>, 6 am Manila (covers <what>)`
2. `h2`: one-line headline
3. `lead`: under 120 words, plain English. End by saying whether any fund rating changed.
4. `thead`: cells `What happened` / `Funds affected` / `What it means`
5. 3 to 6 `tr` rows. Cell 1: bold opening phrase run + a facts run. Cell 2: fund links
   (`{"text":"13","href":"#f13"}`, with `{"text":" "}` runs between them). Cell 3: what it means for those funds.
   The last row is `Coming up (Manila):` with dates in Manila time.
6. `p`: `Sources: ` then linked sources (`{"text":"CNBC (oil)","href":"https://..."}`) separated by `{"text":" · "}`.
7. `details` block (`Earlier updates`), then `dt` blocks (`in_details: true`).

Before writing the new update, turn the previous one into a new FIRST `dt` under Earlier updates:
`label` = its date (e.g. `9 Nov`), `runs` = bold headline run + a one- or two-sentence summary ending
`No change.` (or the rating change). Keep at most 20 `dt` entries. The `27 Oct` "Report first published"
entry always stays last; drop the oldest others.

### Other places to refresh

- `header`: the `meta` block starting `News updated` → `News updated D Mon YYYY, 6 am Manila (markets to <Ddd D Mon> close)`.
  The 3rd and 4th `fact` blocks → the two most telling current figures (e.g. S&P 500 % below its 7,818.93 record
  of 6 Oct 2026). Update the header `lead` if a figure in it is stale.
- `dipbuy`: the `Where we are now:` sentence → latest S&P 500 close, % below the 7,819 record, which levels
  (−5% ≈ 7,430, −10% ≈ 7,040, −20% ≈ 6,255) have been passed and how far the next one is.
- `otherrisks`: when there is material news, add a dated sentence to the relevant risk paragraph. If a paragraph
  passes about 250 words, trim its oldest details. `Dates to watch` (`dt` blocks): remove past dates, add new ones.
- `context`: keep the "<Month> so far." paragraph current; start a new one when the month changes.
- `summary` callouts: change only if one is now wrong.
- Fund ratings live in `data/funds.json` (`other_risk_level`, `overall_risk`, `overall_score`, notes). Change them
  only for a clear, lasting change; say so in the lead and the dt entry, and update any counts that mention them
  (e.g. "11 funds rate High or Very high" in the header lead and facts).

## 5. Rules

- Present the 28 funds simply as a comprehensive set, chosen because together they cover every major asset class,
  region and currency. Never name any organisation, employer, scheme, administrator or nominee connected with them,
  and never describe them as a plan's menu or address "members" (say "investors", e.g. "USD-based investors").
- The site covers the 28 funds only. Never add anyone's personal portfolio, allocations or personal advice.
- Do not add a "Fund it from" column to the Buying a dip tab.
- Plain English, short sentences, units on every number, Manila times.
- Paraphrase sources. Any quote must be under 15 words, and at most one quote per source.
- Do not edit `index.html`, the scripts or the workflow unless something is broken.

## 6. Check, publish, verify

1. `python3 scripts/check_review.py` must print `OK`. Fix anything it reports.
2. `git add -A && git commit` with message `News update <D Mon>` and the attribution lines from your system reminder.
3. `git pull --rebase && git push`.
4. Find the run: `gh run list -R Arshad-investment/Fund-Tracker -L 3`, then poll
   `gh run view <id> -R Arshad-investment/Fund-Tracker --json status,conclusion` until it completes. It must succeed.
5. Reply in 3 to 5 lines: what changed, any rating change, and a Sources list. If something failed, say what,
   and do not push a broken file.

## The 28 funds (`#fN` links)

| # | Fund | Segment |
|---|---|---|
| 1 | BGF World Gold D2 USD | Gold miners |
| 2 | iShares Developed Real Estate Index | Listed real estate |
| 3 | iShares Developed World Index D EUR | Developed world |
| 4 | iShares Developed World Index D Acc USD | Developed world |
| 5 | iShares Europe ex-UK Index | Europe ex-UK |
| 6 | iShares North America Index | US & Canada |
| 7 | iShares Pacific Index | Pacific ex-Japan |
| 8 | iShares UK Index | UK |
| 9 | iShares Global Government Bond Index | Global government bonds |
| 10 | USD Cash Account | Cash |
| 11 | Goldman Sachs Yen Liquid Reserves | JPY money market |
| 12 | GS Quartix Bloomberg Commodity | Commodities |
| 13 | HSBC Islamic Global Equity Index | Shariah global equity |
| 14 | Insight USD Liquidity | USD money market |
| 15 | Insight EUR Liquidity | EUR money market |
| 16 | Fulcrum Diversified Absolute Return | Absolute return |
| 17 | L&G Diversified USD | Multi-asset |
| 18 | L&G Diversified EUR | Multi-asset |
| 19 | NT World Climate Equity Index | Climate-tilted world equity |
| 20 | Pimco Global IG Credit USD | Global IG corporate bonds |
| 21 | Pimco Global IG Credit EUR | Global IG corporate bonds |
| 22 | Robeco QI Emerging Markets Active Equities | Emerging markets |
| 23 | Schroder Asian Local Currency Bond | Asian local-currency bonds |
| 24 | Schroder Asian Opportunities | Asia ex-Japan equity |
| 25 | Vanguard Global Bond Index EUR-hedged | Global aggregate bonds |
| 26 | Vanguard Global Bond Index USD-hedged | Global aggregate bonds |
| 27 | Vanguard Japan Stock Index | Japan equity |
| 28 | Vanguard US Government Bond Index | US Treasuries |

## File format (`data/review.json`)

Each block: `seq` (int), `section`, `kind`, plus `runs` (list of `{text, bold?, italic?, href?, cls?}`),
`label` (runs), `cells` (list of run lists, for `thead`/`tr`), `tone`, `in_details`, `group`.
Blocks are drawn per section in `seq` order. Look at existing blocks and copy their shape.
