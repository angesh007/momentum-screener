"""Trade plan + buy/sell signal, derived from what the screener already measured.

Nothing here fetches data or re-scores a pillar: the inputs are the five
pillars, the 1-min setup (paid plan) and today's quote (open / high / low).

Signal ladder (long-only momentum, so "sell" means "avoid / exit a long"):
  strong_buy  in play + RVol measured and passing + an active chart setup
              with a 2:1 plan + holding above the open
  buy         in play (RVol may be unverified) and not fading below the open
  hold        everything else that is still green on the day
  sell        below the open and either red on the day or stuck in the bottom of the range
  strong_sell gapping down by at least the gap threshold and below the open
"""
from __future__ import annotations

from typing import Optional

from .models import Pillar, Setup, SignalKind, SignalReason, Thresholds, TradePlan
from .patterns import REWARD_RISK, r_levels

NEAR_HIGH = 0.8        # top 20% of the day's range = holding the highs
FADING = 0.35          # bottom 35% of the range = sellers in control
TIGHT_STOP_PCT = 5.0   # stop within 5% of entry
WIDE_STOP_PCT = 10.0   # stop more than 10% away — size down or wait for a pullback


def _r2(x: float) -> float:
    return round(x, 2)


def range_position(price: Optional[float], high: Optional[float], low: Optional[float]) -> Optional[float]:
    """0 = at the low of day, 1 = at the high of day."""
    if price is None or high is None or low is None or high <= low:
        return None
    return max(0.0, min(1.0, (price - low) / (high - low)))


def build_plan(setup: Optional[Setup], price: Optional[float], gap: Optional[float],
               high: Optional[float], low: Optional[float],
               prev_close: Optional[float]) -> Optional[TradePlan]:
    """Prefer the chart setup's levels; otherwise a high-of-day break plan from the quote."""
    if setup and setup.pattern != "none" and setup.entry and setup.stop and setup.risk:
        return TradePlan(
            source="setup", entry=setup.entry, stop=setup.stop,
            scale_out=setup.scale_out, target=setup.target, risk=setup.risk,
            reward_risk=setup.reward_risk or REWARD_RISK,
            risk_pct=_r2(setup.risk / setup.entry * 100),
            note=f"{'Bull flag' if setup.pattern == 'bull_flag' else 'Flat top'} ({setup.stage}) on 1-min candles.",
        )
    # Long-only: no plan for a stock that is red on the day or has no range yet.
    if not (price and high and low and gap is not None) or gap <= 0 or high <= low:
        return None
    if prev_close and price < prev_close:
        return None
    entry = max(high, price)          # break of the high of day
    stop = low                        # below the low of day
    risk, scale_out, target = r_levels(entry, stop)
    if risk <= 0:
        return None
    return TradePlan(
        source="day_range", entry=_r2(entry), stop=_r2(stop), scale_out=_r2(scale_out),
        target=_r2(target), risk=_r2(risk), reward_risk=REWARD_RISK,
        risk_pct=_r2(risk / entry * 100),
        note="From today's range (no intraday candles): entry on a break of the high of day, "
             "stop under the low of day. Tighten the stop to the 1-min pullback low on your chart and re-size.",
    )


def evaluate(pillars: list[Pillar], in_play: bool, th: Thresholds, price: Optional[float],
             gap: Optional[float], open_: Optional[float], high: Optional[float], low: Optional[float],
             setup: Optional[Setup], plan: Optional[TradePlan]) -> tuple[SignalKind, list[SignalReason], str]:
    st = {p.key: p for p in pillars}
    reasons: list[SignalReason] = []

    def add(factor, label, impact, detail=""):
        reasons.append(SignalReason(factor=factor, label=label, impact=impact, detail=detail))

    # --- pillars --------------------------------------------------------------
    passed = sum(1 for p in pillars if p.status == "pass")
    failed = [p.label for p in pillars if p.status == "fail"]
    if in_play:
        add("pillars", f"In play — {passed}/5 pillars pass", "positive",
            "Every measurable pillar passes or is close." if passed < 5 else "All five pillars pass.")
    else:
        add("pillars", f"{passed}/5 pillars pass", "negative" if failed else "neutral",
            f"Failing: {', '.join(failed)}." if failed else "")

    # --- relative volume -------------------------------------------------------
    rv = st.get("rvol")
    rvol_measured = rv is not None and rv.status != "unknown"
    if rv is not None:
        if rv.status == "pass":
            add("rvol", f"Relative volume {rv.display}", "positive", f"At or above the {th.rvol_min:g}× cut-off. {rv.note}")
        elif rv.status == "warn":
            add("rvol", f"Relative volume {rv.display}", "neutral", f"Below the {th.rvol_min:g}× cut-off. {rv.note}")
        elif rv.status == "fail":
            add("rvol", f"Relative volume {rv.display}", "negative", f"Well below {th.rvol_min:g}× — not enough interest. {rv.note}")
        else:
            add("rvol", "Relative volume unverified", "neutral", rv.note)

    # --- price momentum --------------------------------------------------------
    if gap is not None:
        if gap >= th.gap_pct_min:
            add("momentum", f"Up {gap:.1f}% on the day", "positive", f"Gap ≥ {th.gap_pct_min:g}%.")
        elif gap > 0:
            add("momentum", f"Up {gap:.1f}% on the day", "neutral", f"Below the {th.gap_pct_min:g}% gap threshold.")
        else:
            add("momentum", f"Down {abs(gap):.1f}% on the day", "negative", "No long momentum while red on the day.")

    # --- trend: price vs open, and vs the 9 EMA when candles give us one ------
    above_open = None
    if price is not None and open_:
        above_open = price >= open_
        move = (price - open_) / open_ * 100
        add("trend", f"{'Above' if above_open else 'Below'} the open ({move:+.1f}%)",
            "positive" if above_open else "negative",
            "Buyers have held the move since the open." if above_open else "Selling since the open.")
    if setup and setup.ema9 and price is not None:
        above = price >= setup.ema9
        add("trend", f"{'Above' if above else 'Below'} the 9 EMA ({setup.ema9:.2f})",
            "positive" if above else "negative")

    # --- breakout strength: where in today's range the price sits ------------
    pos = range_position(price, high, low)
    fading = pos is not None and pos <= FADING
    if pos is not None:
        off_high = (high - price) / high * 100
        if pos >= NEAR_HIGH:
            add("breakout", f"Holding near the high of day ({off_high:.1f}% off)", "positive",
                f"High {high:.2f} is the breakout level.")
        elif fading:
            add("breakout", f"Fading — {off_high:.1f}% off the high", "negative",
                "In the bottom third of today's range.")
        else:
            add("breakout", f"Mid-range, {off_high:.1f}% off the high", "neutral")
    if setup and setup.pattern != "none":
        name = "Bull flag" if setup.pattern == "bull_flag" else "Flat top"
        add("setup", f"{name} — {setup.stage}", "positive", " ".join(setup.notes))
    elif setup:
        add("setup", "No clean chart setup", "neutral", " ".join(setup.notes))

    # --- risk / reward ---------------------------------------------------------
    if plan:
        tight = plan.risk_pct <= TIGHT_STOP_PCT
        wide = plan.risk_pct > WIDE_STOP_PCT
        add("risk_reward", f"{plan.reward_risk:g}:1 plan, stop {plan.risk_pct:.1f}% below entry",
            "positive" if tight else "negative" if wide else "neutral",
            "Tight stop." if tight else "Wide stop — size down or wait for a pullback." if wide else "")

    # --- catalyst --------------------------------------------------------------
    cat = st.get("catalyst")
    if cat is not None:
        add("catalyst", "Fresh catalyst" if cat.status == "pass" else "No fresh catalyst",
            "positive" if cat.status == "pass" else "negative", cat.note)

    # --- classify --------------------------------------------------------------
    below_open = above_open is False
    has_setup = bool(setup and setup.pattern != "none")
    rvol_pass = rv is not None and rv.status == "pass"
    good_rr = bool(plan and plan.reward_risk >= REWARD_RISK and plan.risk_pct <= WIDE_STOP_PCT)

    if gap is not None and gap <= -th.gap_pct_min and (below_open or above_open is None):
        signal: SignalKind = "strong_sell"
    elif below_open and (fading or (gap is not None and gap < 0)):
        signal = "sell"
    elif in_play and rvol_pass and has_setup and good_rr and not below_open and not fading:
        signal = "strong_buy"
    elif in_play and not below_open:
        signal = "buy"
    else:
        signal = "hold"

    note = ""
    if signal == "buy":
        missing = []
        if not rvol_measured:
            missing.append("measured relative volume (needs intraday candles)")
        elif not rvol_pass:
            missing.append(f"relative volume ≥ {th.rvol_min:g}×")
        if not has_setup:
            missing.append("an active bull-flag / flat-top setup")
        if not good_rr:
            missing.append(f"a 2:1 plan with a stop within {WIDE_STOP_PCT:g}%")
        if fading:
            missing.append("price holding off the lows")
        if missing:
            note = "Strong buy needs " + ", ".join(missing) + "."
    elif signal == "strong_sell":
        note = "Gapping down and below the open — avoid longs; exit if holding."
    elif signal == "sell":
        note = "Below the open with sellers in control — avoid longs; exit if holding."
    elif signal == "hold" and gap is not None and gap < 0:
        note = "Red on the day but holding above the open — no long setup until it turns green."
    elif signal == "hold" and not in_play:
        note = "Not in play — a buy needs every measurable pillar to pass."
    elif signal == "hold" and below_open:
        note = "In play but trading below the open — wait for it to reclaim."
    return signal, reasons, note
