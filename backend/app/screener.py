"""Step 1: the five pillars, evaluated per symbol."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from .data import market
from .models import Candle, NewsItem, Pillar, ScreenResult, Thresholds
from .patterns import detect_setup
from .session import ET
from .signals import build_plan, evaluate

log = logging.getLogger("screener")


def _today_volume(candles: list[Candle]) -> Optional[float]:
    """Volume traded so far today (ET). The candle window reaches back 8 hours,
    which before ~04:00 ET would otherwise count yesterday's after-hours."""
    today = datetime.now(ET).date()
    vol = sum(c.v for c in candles if datetime.fromtimestamp(c.t, ET).date() == today)
    return vol or None


def _fmt_shares(n: Optional[float]) -> str:
    if n is None:
        return "—"
    return f"{n/1e6:.1f}M"


async def screen_symbol(symbol: str, th: Thresholds, include_setup: bool) -> ScreenResult:
    symbol = symbol.upper().strip()
    try:
        quote, profile, metrics, news = await asyncio.gather(
            market.quote(symbol),
            market.profile(symbol),
            market.metrics(symbol),
            market.news(symbol, th.news_lookback_hours),
        )
    except Exception as e:  # network / key problems surface per-row, not as a 500
        log.warning("screen %s failed: %s", symbol, e)
        return ScreenResult(symbol=symbol, pillars=[], score=0, in_play=False, error=str(e))

    price = quote.get("c") or None
    gap = quote.get("dp")
    shares_out = (profile.get("shareOutstanding") or 0) * 1e6 or None
    # Live market value; Finnhub's profile figure (in millions) is as of the last close.
    market_cap = (price * shares_out) if (price and shares_out) else ((profile.get("marketCapitalization") or 0) * 1e6 or None)
    open_, high, low, prev_close = (quote.get(k) or None for k in ("o", "h", "l", "pc"))
    avg_vol = (metrics.get("10DayAverageTradingVolume") or metrics.get("3MonthAverageTradingVolume") or 0) * 1e6 or None

    candles: list[Candle] = []
    if include_setup or avg_vol:
        try:
            candles = await market.candles_1m(symbol)
        except Exception as e:
            log.info("candles unavailable for %s: %s", symbol, e)

    today_vol = _today_volume(candles) if candles else None
    rvol = (today_vol / avg_vol) if (today_vol and avg_vol) else None

    pillars = [
        _price_pillar(price, th),
        _gap_pillar(gap, th),
        _rvol_pillar(rvol, today_vol, avg_vol, th),
        _float_pillar(shares_out, th),
        _catalyst_pillar(news, th),
    ]
    score = sum(1 for p in pillars if p.status == "pass") + sum(0.5 for p in pillars if p.status == "warn")
    # Relative volume needs intraday candles (Finnhub paid). If it can't be
    # measured, the other four decide and the row is flagged as unverified.
    in_play = all(p.status in ("pass", "warn") or (p.key == "rvol" and p.status == "unknown") for p in pillars)

    setup = detect_setup(candles) if (include_setup and candles) else None
    plan = build_plan(setup, price, gap, high, low, prev_close)
    signal, reasons, signal_note = evaluate(pillars, in_play, th, price, gap, open_, high, low, setup, plan)

    return ScreenResult(
        symbol=symbol,
        name=profile.get("name", ""),
        price=price,
        gap_pct=gap,
        rvol=round(rvol, 2) if rvol else None,
        today_volume=today_vol,
        avg_volume=avg_vol,
        shares_outstanding=shares_out,
        market_cap=market_cap,
        open=open_,
        high=high,
        low=low,
        prev_close=prev_close,
        quote_time=quote.get("t") or None,
        pillars=pillars,
        score=int(score * 2),  # 0–10 so half-credit stays an integer
        in_play=in_play,
        catalyst=news[0] if news else None,
        news_count=len(news),
        setup=setup,
        plan=plan,
        signal=signal,
        signal_reasons=reasons,
        signal_note=signal_note,
    )


def _price_pillar(price, th) -> Pillar:
    if price is None:
        return Pillar(key="price", label="Price", status="unknown", display="—")
    if price < 1:
        return Pillar(key="price", label="Price", status="fail", value=price, display=f"${price:.2f}",
                      note="Under $1 — avoided as a messy distraction")
    ok = th.price_min <= price <= th.price_max
    return Pillar(
        key="price", label="Price", status="pass" if ok else "fail", value=price,
        display=f"${price:.2f}", note=f"Target ${th.price_min:g}–${th.price_max:g}",
    )


def _gap_pillar(gap, th) -> Pillar:
    if gap is None:
        return Pillar(key="gap", label="Gap", status="unknown", display="—")
    status = "pass" if gap >= th.gap_pct_min else ("warn" if gap >= th.gap_pct_min * 0.5 else "fail")
    return Pillar(
        key="gap", label="Gap", status=status, value=gap,
        display=f"{gap:+.1f}%", note=f"Needs ≥ {th.gap_pct_min:g}% from prior close",
    )


def _rvol_pillar(rvol, today_vol, avg_vol, th) -> Pillar:
    if rvol is None:
        note = ("Needs intraday candles — a Finnhub paid plan. Check RVol on your scanner."
                if market.candles_blocked else "No intraday volume yet" if avg_vol else "No average volume from Finnhub")
        return Pillar(key="rvol", label="Rel. volume", status="unknown", display="N/A", note=note)
    status = "pass" if rvol >= th.rvol_min else ("warn" if rvol >= th.rvol_min * 0.5 else "fail")
    return Pillar(
        key="rvol", label="Rel. volume", status=status, value=rvol,
        display=f"{rvol:.1f}×", note=f"{today_vol/1e6:.2f}M today vs {avg_vol/1e6:.2f}M avg",
    )


def _float_pillar(shares, th) -> Pillar:
    if shares is None:
        return Pillar(key="float", label="Float", status="unknown", display="—")
    if shares <= th.float_ideal:
        status = "pass"
    elif shares <= th.float_max:
        status = "warn"
    else:
        status = "fail"
    return Pillar(
        key="float", label="Float", status=status, value=shares, display=_fmt_shares(shares),
        note="Shares outstanding (Finnhub free tier has no true float)",
    )


def _catalyst_pillar(news: list[NewsItem], th) -> Pillar:
    if not news:
        return Pillar(
            key="catalyst", label="Catalyst", status="fail", value=0, display="none",
            note=f"No headlines in the last {th.news_lookback_hours}h",
        )
    return Pillar(
        key="catalyst", label="Catalyst", status="pass", value=len(news),
        display=f"{len(news)} headline{'s' if len(news) != 1 else ''}", note=news[0].headline,
    )


async def screen_many(symbols: list[str], th: Thresholds, include_setups: bool) -> list[ScreenResult]:
    seen, ordered = set(), []
    for s in symbols:
        s = s.upper().strip()
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)
    sem = asyncio.Semaphore(4)

    async def run(s):
        async with sem:
            return await screen_symbol(s, th, include_setups)

    results = await asyncio.gather(*(run(s) for s in ordered))
    return sorted(results, key=lambda r: (r.error is not None, -r.score, -(r.gap_pct or 0)))
