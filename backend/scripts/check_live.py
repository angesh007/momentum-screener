"""Verify the Finnhub key and every endpoint the app uses, against live data.

    cd backend && .venv/bin/python -m scripts.check_live [SYMBOL]
"""
import asyncio
import sys
import time

sys.path.insert(0, ".")
from app.config import settings  # noqa: E402
from app.data import market  # noqa: E402


def ok(label, detail=""):
    print(f"  ✔ {label}  {detail}")


def bad(label, detail=""):
    print(f"  ✘ {label}  {detail}")


async def main(symbol: str):
    print(f"Finnhub key: {'set (' + settings.finnhub_api_key[:6] + '…)' if settings.finnhub_api_key else 'MISSING'}")
    if not settings.finnhub_api_key or "paste_your" in settings.finnhub_api_key:
        bad("No key in backend/.env"); return 1
    print(f"Checking {symbol}…")
    failures = 0
    try:
        q = await market.quote(symbol)
        if q.get("c"):
            ok("quote", f"price {q['c']}  change {q.get('dp')}%")
        else:
            bad("quote", f"empty response {q} — wrong key or symbol?"); failures += 1
    except Exception as e:
        bad("quote", str(e)); return 1
    try:
        p = await market.profile(symbol)
        ok("profile2", f"{p.get('name')}  shares out {p.get('shareOutstanding')}M")
    except Exception as e:
        bad("profile2", str(e)); failures += 1
    try:
        m = await market.metrics(symbol)
        ok("metric", f"10d avg vol {m.get('10DayAverageTradingVolume')}M")
    except Exception as e:
        bad("metric", str(e)); failures += 1
    try:
        n = await market.news(symbol, 48)
        ok("company-news", f"{len(n)} headlines in 48h")
    except Exception as e:
        bad("company-news", str(e)); failures += 1
    c = await market.candles_1m(symbol)
    if c:
        ok("1-min candles", f"{len(c)} candles (paid plan)")
    elif market.candles_blocked:
        print("  – 1-min candles  not on the free plan → RVol and setups show as unavailable (expected)")
    else:
        print("  – 1-min candles  empty (normal outside US market hours)")
    await market.close()
    print("\nAll good — start the app." if not failures else f"\n{failures} check(s) failed, see above.")
    return failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "AAPL")))
