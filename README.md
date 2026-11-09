# Fund tracker

A free website that tracks the latest prices, returns and risk ratings for 28 funds from 16 providers, together with the full fund review: summary, daily update, AI-crash scenario, other risks, market context, fund-by-fund analysis, buying-a-dip guide, fund menu and sources.
Every morning a GitHub Action fetches new prices, saves them, and republishes the site. No server, no cost.

## What's in here

| File | What it does |
|---|---|
| `index.html` | The website. Reads the data files and draws the charts and table. |
| `data/funds.json` | Each fund's details, review analysis and the web pages its price is read from. You edit this by hand. |
| `data/review.json` | The full text of the fund review, section by section (Summary, Today, Other risks and the other tabs). |
| `data/prices.json` | Latest price per fund. The robot updates this; you don't need to touch it. |
| `data/history.csv` | Every new price is added here, building a price history over time. |
| `scripts/update_prices.py` | The robot: visits each price page, reads the NAV, saves it. |
| `tests/test_parsers.py` | Quick checks that the price readers still understand each site. |
| `.github/workflows/update.yml` | The schedule: runs the robot every morning and publishes the site. |

## Put it online (one time, about 10 minutes)

1. **Make a free GitHub account** at github.com if you don't have one.
2. **Create a new repository**: click **+** (top right) → **New repository**. Name it `fund-tracker`, choose **Public** (free GitHub Pages needs a public repository), and click **Create repository**.
3. **Upload the files**: on the new repository's page click **uploading an existing file**. Drag in everything from this folder, *including the hidden `.github` folder* (on a Mac press Cmd+Shift+. in Finder to see it; on Windows tick "Hidden items" in File Explorer's View menu). Click **Commit changes**.
   - If the `.github` folder won't drag in: click **Add file → Create new file**, type `.github/workflows/update.yml` as the name, paste in the contents of that file, and commit.
4. **Turn on the website**: **Settings → Pages**. Under **Build and deployment → Source**, choose **GitHub Actions**.
5. **Run it once**: **Actions** tab → if asked, click **I understand my workflows, go ahead and enable them** → **Update prices and publish** → **Run workflow**.
6. After a minute or two the run turns green. Your site is at `https://YOUR-USERNAME.github.io/fund-tracker/`. That link is in **Settings → Pages** too.

From then on it updates itself every morning: prices four times a day from 5:40 am Manila time, and the news by about 6 am (see NEWS_UPDATE.md).

## Checking on the robot

- **Actions** tab → click the latest run → the summary lists every fund as `OK` or `FAIL`.
- A `FAIL` keeps that fund's last good price, and the site marks it "Not updated". Nothing breaks.
- Price pages change their layout now and then, which makes a reader fail. Copy the `FAIL` line and ask Claude to fix the reader or switch that fund to another price page.

## Common changes

- **Different update time**: edit the `cron` line in `.github/workflows/update.yml`. The time is in UTC (Manila is UTC+8). [crontab.guru](https://crontab.guru) helps.
- **A fund's price comes from the wrong page or share class**: edit its `sources` list in `data/funds.json`. Each source is a `parser` (`finanzen`, `ishares` or `vanguard`) and a `url`.
- **Update a price by hand** (for funds with no public price): edit that fund's entry in `data/prices.json`.
- **Update the review ratings**: edit the fund in `data/funds.json`.

Any edit you commit on GitHub republishes the site automatically.

## Run it on your own computer (optional)

```
pip install requests
python tests/test_parsers.py        # checks the price readers
python scripts/update_prices.py     # fetches prices into data/
python -m http.server 8000          # then open http://localhost:8000
```

Opening `index.html` by double-clicking won't load the data. Browsers block that, which is why you need the small server above.

## Good to know

- **The repository is public**, so anyone can see these files. Don't add personal holdings, balances or names.
- **GitHub pauses scheduled runs** in a repository with no activity for 60 days. The robot's own price commits normally count as activity. If updates ever stop, open **Actions** and re-enable the workflow.
- **Fair use of the price sites**: the robot visits about 25 pages once a day, pausing between them. Keep it that way.

Research, not personal advice.
