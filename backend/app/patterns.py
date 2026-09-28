"""Step 2 + Step 5 of the strategy on 1-minute candles.

- Bull flag / micro-pullback: surge on volume, shallow pullback on lighter
  volume, entry when a candle breaks the prior candle's high.
- Flat top breakout: repeated rejections at one price level, entry on the
  break of that level with volume.
- Stop = low of the pullback or the 9 EMA, whichever is tighter above zero.
- Target = entry + 2 * risk (2:1 reward-to-risk).
"""
from __future__ import annotations

from typing import Optional

from .models import Candle, Setup


def ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _round(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 2)


REWARD_RISK = 2.0


def r_levels(entry: float, stop: float) -> tuple[float, float, float]:
    """(risk, scale_out at +1R, target at +2R) — the Step 5 exit plan."""
    risk = entry - stop
    return risk, entry + risk, entry + REWARD_RISK * risk


def detect_setup(candles: list[Candle]) -> Setup:
    if len(candles) < 15:
        return Setup(pattern="none", stage="not enough candles", notes=["Need at least 15 one-minute candles."])

    closes = [c.c for c in candles]
    ema9 = ema(closes, 9)
    last = candles[-1]
    prev = candles[-2]

    flag = _bull_flag(candles, ema9)
    if flag:
        return flag
    top = _flat_top(candles, ema9)
    if top:
        return top

    return Setup(
        pattern="none",
        stage="no clean setup",
        ema9=_round(ema9[-1]),
        notes=["No micro-pullback or flat top in the last 30 candles. Wait, don't chase."],
    )


def _bull_flag(candles: list[Candle], ema9: list[float]) -> Optional[Setup]:
    window = candles[-30:]
    e9 = ema9[-30:]
    n = len(window)
    # Find the strongest 3–8 candle impulse in the window.
    best = None
    for i in range(n - 4):
        for j in range(i + 3, min(i + 9, n)):
            gain = (window[j].h - window[i].l) / max(window[i].l, 1e-9)
            if gain >= 0.04:
                vol = sum(c.v for c in window[i : j + 1]) / (j - i + 1)
                if best is None or gain > best[2]:
                    best = (i, j, gain, vol)
    if not best:
        return None
    i, j, gain, impulse_vol = best
    pole_low, pole_high = window[i].l, window[j].h
    pullback = window[j + 1 :]
    if not (2 <= len(pullback) <= 8):
        return None

    pb_low = min(c.l for c in pullback)
    pb_vol = sum(c.v for c in pullback) / len(pullback)
    retrace = (pole_high - pb_low) / max(pole_high - pole_low, 1e-9)
    if retrace > 0.6 or pb_vol > impulse_vol * 0.8:
        return None

    last, prev = pullback[-1], pullback[-2] if len(pullback) > 1 else window[j]
    breaking = last.c > prev.h
    entry = prev.h if not breaking else last.c
    stop = max(pb_low, e9[-1]) if e9[-1] < entry else pb_low
    risk, scale_out, target = r_levels(entry, stop)
    if risk <= 0:
        return None
    notes = [
        f"Pole gained {gain*100:.1f}% over {j-i+1} candles.",
        f"Pullback retraced {retrace*100:.0f}% on {pb_vol/impulse_vol*100:.0f}% of impulse volume.",
        "Entry: break of the previous candle's high." if not breaking else "Previous candle high already broken.",
    ]
    return Setup(
        pattern="bull_flag",
        stage="breaking" if breaking else "forming",
        entry=_round(entry), stop=_round(stop), scale_out=_round(scale_out), target=_round(target),
        risk=_round(risk), reward_risk=REWARD_RISK, ema9=_round(e9[-1]), notes=notes,
    )


def _flat_top(candles: list[Candle], ema9: list[float], tol: float = 0.006) -> Optional[Setup]:
    window = candles[-25:]
    highs = [c.h for c in window]
    ceiling = max(highs)
    touches = [c for c in window if abs(c.h - ceiling) / ceiling <= tol]
    if len(touches) < 2:
        return None
    last = window[-1]
    if last.c < ceiling * 0.97:
        return None  # too far below the ceiling to count as consolidation
    breaking = last.c > ceiling
    consolidation_low = min(c.l for c in window[-8:])
    entry = ceiling if not breaking else last.c
    stop = max(consolidation_low, ema9[-1]) if ema9[-1] < entry else consolidation_low
    risk, scale_out, target = r_levels(entry, stop)
    if risk <= 0:
        return None
    avg_vol = sum(c.v for c in window[:-1]) / max(len(window) - 1, 1)
    vol_ok = last.v >= avg_vol * 1.5
    notes = [
        f"Resistance at {ceiling:.2f} tested {len(touches)} times.",
        "Breakout volume is heavy." if vol_ok else "Breakout volume is light — be careful.",
    ]
    return Setup(
        pattern="flat_top",
        stage="breaking" if breaking else "consolidating",
        entry=_round(entry), stop=_round(stop), scale_out=_round(scale_out), target=_round(target),
        risk=_round(risk), reward_risk=REWARD_RISK, ema9=_round(ema9[-1]), notes=notes,
    )
