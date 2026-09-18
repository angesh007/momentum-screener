"""Run a full five-pillar scan from the terminal (no frontend needed).

    cd backend && .venv/bin/python -m scripts.live_scan            # scans universe.txt
    cd backend && .venv/bin/python -m scripts.live_scan SOUN BBAI  # your own tickers
"""
import asyncio
import sys

sys.path.insert(0, ".")
from app.data import market  # noqa: E402
from app.models import Thresholds  # noqa: E402
from app.screener import screen_many  # noqa: E402
from app.session import market_session  # noqa: E402

GLYPH = {"pass": "●", "warn": "◐", "fail": "○", "unknown": "?"}


async def main(symbols):
    th = Thresholds()
    s = market_session()
    print(f"{s['et_time']} ET · {s['phase']} · {s['advice']}")
    if not symbols:
        from app.main import load_universe
        symbols = load_universe()
        print(f"Scanning universe.txt: {' '.join(symbols)}")
    res = await screen_many(symbols, th, include_setups=True)
    print(f"\n{'SYM':6} {'PRICE':>7} {'GAP':>7} {'RVOL':>6} {'FLOAT':>7}  PILLARS  SETUP")
    for r in res:
        if r.error:
            print(f"{r.symbol:6} error: {r.error}"); continue
        pil = "".join(GLYPH[p.status] for p in r.pillars)
        setup = f"{r.setup.pattern} {r.setup.stage}" if r.setup and r.setup.pattern != "none" else "-"
        flt = f"{r.shares_outstanding/1e6:.0f}M" if r.shares_outstanding else "-"
        print(f"{r.symbol:6} {r.price or 0:7.2f} {r.gap_pct or 0:6.1f}% {r.rvol or 0:6.1f} {flt:>7}  {pil}    {setup}{'  ← IN PLAY' if r.in_play else ''}")
    print("\n● pass  ◐ warn  ○ fail  ? unknown   (price · gap · rvol · float · catalyst)")
    await market.close()


if __name__ == "__main__":
    asyncio.run(main([s.upper() for s in sys.argv[1:]]))
