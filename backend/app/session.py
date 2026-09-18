"""Step 3: timing. Ross trades 9:30–11:30 ET and rarely past midday."""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def market_session() -> dict:
    now = datetime.now(ET)
    minutes = now.hour * 60 + now.minute
    weekday = now.weekday() < 5
    if not weekday:
        phase, advice = "closed", "Markets are closed. Build tomorrow's watchlist."
    elif minutes < 4 * 60:
        phase, advice = "closed", "Pre-market opens at 4:00 ET."
    elif minutes < 9 * 60 + 30:
        phase, advice = "premarket", "Scan for gappers and catalysts. No entries before the open."
    elif minutes < 10 * 60:
        phase, advice = "open", "First 30 minutes: cleanest, highest-volume momentum."
    elif minutes < 11 * 60 + 30:
        phase, advice = "golden", "Golden hours. Trade the setups, honour the stops."
    elif minutes < 16 * 60:
        phase, advice = "midday", "Past 11:30 ET — choppy. Ross rarely trades here."
    elif minutes < 20 * 60:
        phase, advice = "afterhours", "After-hours. Review trades, prep the next list."
    else:
        phase, advice = "closed", "Markets are closed."
    return {
        "et_time": now.strftime("%H:%M:%S"),
        "et_date": now.strftime("%Y-%m-%d"),
        "phase": phase,
        "tradeable": phase in ("open", "golden"),
        "advice": advice,
    }
