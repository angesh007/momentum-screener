# Momentum board

Ross Cameron's small-cap momentum strategy as a runnable app:
**FastAPI** backend on the Finnhub API (nothing else) and **Nuxt 3 / Vue** frontend.

Paste the gappers from your pre-market scanner, and it scores each one against
the five pillars live from Finnhub, spots bull-flag / flat-top setups on
1-minute candles (paid Finnhub plan), and turns a setup into a sized trade plan
with stop, scale-out and 2:1 target.

## How it maps to the strategy

| Step | Rule in the document | What the app does |
|---|---|---|
| 1 · Selection | 5–10 stocks in play; $2–20; gap ≥ 10%; RVol ≥ 5×; float ≤ 10M (≤ 100M hard); fresh catalyst | You supply the candidates (UI box or `universe.txt`); Finnhub scores all five pillars. "In play" = all pass, capped at 10. Stocks under $1 always fail. |
| 2 · Setups | Bull flag / micro-pullback; flat-top breakout; enter on break of prior candle high | `patterns.py` detects both on 1-min candles and reports the entry trigger and stage. Needs Finnhub candles (paid plan); on the free plan the UI says so and you read the chart on your broker. |
| 3 · Timing | 9:30–11:30 ET; first 30 min cleanest; avoid midday | Live ET clock + session banner. Outside the window the trade plan is marked "plan only". Optional rescan every minute. |
| 4 · Level 2 | Watch ask walls and bid support | Not available from Finnhub — the UI reminds you to confirm on your broker's Level 2 before entering. |
| 5 · Risk | Stop at pullback low / 9 EMA; 2:1 target; sell half into strength, stop to break-even | Stop, +1R scale-out and +2R target are computed per setup. The position sizer turns a dollar risk into share count and the four-step exit plan. |

## Quick start (3 commands)

You need Python 3.11+ and Node 18+.

```bash
git clone <this repo> && cd momentum-screener
cp backend/.env.example backend/.env    # then paste your Finnhub key into it
./run.sh                                # installs on first run, then starts both servers
```

Open **http://localhost:3000**. The API is on http://localhost:8000 (docs at `/docs`).

Windows: `powershell -ExecutionPolicy Bypass -File run.ps1`.

### Getting the free Finnhub key

1. Go to https://finnhub.io/register and create an account (email + password, no card).
2. The dashboard shows your API key. Copy it.
3. In `backend/.env` replace `paste_your_finnhub_key_here` with the key.

`backend/.env.example` is the template; `run.sh` copies it to `.env` for you and
refuses to start until the placeholder is replaced.

### Other ways to run

```bash
make setup && make dev          # same as run.sh, via Make
make backend                    # backend only  (uvicorn, port 8000)
make frontend                   # frontend only (nuxt dev, port 3000)
docker compose up --build       # both in containers (needs backend/.env)
```

Manual, step by step:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # add FINNHUB_API_KEY
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm install
cp .env.example .env
npm run dev
```

## Testing with live data

Do this once after adding the key, before opening the UI.

**1. Verify the key and every endpoint (≈10 seconds)**

```bash
cd backend && source .venv/bin/activate
python -m scripts.check_live           # or: python -m scripts.check_live SOUN
```

Expected output:

```
Finnhub key: set (dal9gd…)
Checking AAPL…
  ✔ quote  price 231.4  change 0.8%
  ✔ profile2  Apple Inc  shares out 15022.0M
  ✔ metric  10d avg vol 48.1M
  ✔ company-news  14 headlines in 48h
  – 1-min candles  not on the free plan → RVol and setups show as unavailable (expected)
All good — start the app.
```

A ✘ on `quote` means the key is wrong. The candles line is informational: the free plan doesn't include them.

**2. Run a full scan in the terminal**

```bash
python -m scripts.live_scan             # scores everything in universe.txt
python -m scripts.live_scan SOUN BBAI   # or your own tickers
```

**3. Unit tests (no network, no key needed)**

```bash
cd backend && python -m pytest
```

**4. Open the UI** — `./run.sh`, then http://localhost:3000. The header shows
"Connected to Finnhub · live data" when the key validates. The interactive API
docs at http://localhost:8000/docs let you fire any endpoint by hand.

**When to test.** US pre-market starts 04:00 ET and the golden hours are
09:30–11:30 ET. In India that is 13:30 IST for pre-market and **19:00–21:00 IST**
for the golden hours (18:00–20:00 IST during US winter time, roughly November
to March). Outside those hours the app runs but gap % reflects yesterday's move — that is
the filter working, not a bug.

## Using it

- Paste today's gappers into the box (pre-filled from `backend/universe.txt`) and **Scan**. Up to 40 tickers per scan.
- **Edit thresholds** — every pillar cut-off is adjustable.
- **Show the rules** — the five steps with your current thresholds filled in.
- Click a row → pillars, catalyst headlines, the setup (paid plan) and the position sizer.

## What Finnhub's free plan gives you

| Need | Free plan | In the app |
|---|---|---|
| Quote, gap %, name, shares outstanding, avg volume, news | ✔ | Pillars 1, 2, 4, 5 are live. 4 calls per ticker, 60 calls/min → max 40 tickers per scan. |
| Screener endpoint | ✘ | You paste the candidates. |
| 1-minute candles | ✘ (paid) | Relative volume shows "—" and the setup/chart say unavailable. A row can still be "in play" on the other four pillars — it's marked as unverified on RVol. On a paid plan everything switches on with no code change. |
| True float | ✘ | Shares outstanding is used as a proxy, labelled as such. |
| Level 2 / Time & Sales | ✘ | Your broker. |

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | validates the key with a live quote; candle source; session |
| GET | `/api/session` | ET time, phase (premarket / open / golden / midday / afterhours / closed) |
| GET | `/api/universe` | tickers from `universe.txt` |
| POST | `/api/screen` | `{symbols, thresholds, include_setups}` → ranked results + `in_play` (empty `symbols` = universe.txt) |
| GET | `/api/stock/{symbol}` | pillars, setup, last 120 candles, 48h news |

## Project layout

```
backend/app/
  main.py        routes
  data.py        Finnhub client (rate-limited, cached)
  screener.py    five-pillar scoring
  patterns.py    bull flag / flat top / 9 EMA / stop & targets
  session.py     ET trading-window logic
frontend/
  pages/index.vue           board, controls, detail drawer
  components/StockRow.vue   ticker + gap + pillar strip + setup line
  components/PillarStrip.vue, CandleChart.vue, PositionSizer.vue, RulesPanel.vue
  composables/useScreener.ts
```

## Troubleshooting

- **500 `useScreener is not defined`** — the project path contains `(`, `)` or similar (e.g. `…-only(1)`), which breaks Nuxt's file scanning. Rename the folder, delete `frontend/.nuxt`, restart.

- **"Backend isn't reachable"** — start it (`make backend`) and check `NUXT_PUBLIC_API_BASE` in `frontend/.env`.
- **"No Finnhub key found"** — edit `backend/.env`, restart uvicorn.
- **Rel. volume shows "—"** — expected on the free plan (no candles). Check RVol on your scanner.
- **"Nothing to scan"** — the ticker box is empty and `universe.txt` has no tickers.
- **Rate limit errors** — scan fewer tickers; the free plan is 60 calls/min.

Educational tool, not trading advice. Small caps move fast — paper-trade first.
