import time
from datetime import datetime

import httpx
import pytest

from app import screener
from app.models import Candle, NewsItem, Thresholds

from app.session import ET

# At least an hour into the ET day, so candles stamped "minutes ago" are always today.
_midnight_et = datetime.now(ET).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
NOW = max(int(time.time()), int(_midnight_et) + 3600)
NEWS = [NewsItem(headline="FDA clearance", source="x", url="u", published="2026-01-01T00:00:00")]


class FakeMarket:
    candles_blocked = False

    def __init__(self, quote, profile, metrics, news, candles):
        self._q, self._p, self._m, self._n, self._c = quote, profile, metrics, news, candles

    async def quote(self, s): return self._q
    async def profile(self, s): return self._p
    async def metrics(self, s): return self._m
    async def news(self, s, h): return self._n
    async def candles_1m(self, s): return self._c


@pytest.mark.asyncio
async def test_all_pillars_pass(monkeypatch):
    from app.models import NewsItem
    candles = [Candle(t=NOW - 60 * (20 - i), o=5, h=5.1, l=4.9, c=5, v=500_000) for i in range(20)]
    fake = FakeMarket(
        quote={"c": 5.2, "dp": 32.0},
        profile={"name": "Test Co", "shareOutstanding": 8.0},
        metrics={"10DayAverageTradingVolume": 1.0},
        news=[NewsItem(headline="FDA clearance", source="x", url="u", published="2026-01-01T00:00:00")],
        candles=candles,
    )
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("TEST", Thresholds(), include_setup=False)
    assert [p.status for p in r.pillars] == ["pass"] * 5
    assert r.in_play and r.rvol == 10.0


@pytest.mark.asyncio
async def test_sub_dollar_and_no_news_fail(monkeypatch):
    fake = FakeMarket({"c": 0.8, "dp": 40}, {"shareOutstanding": 500}, {}, [], [])
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("JUNK", Thresholds(), include_setup=False)
    st = {p.key: p.status for p in r.pillars}
    assert st["price"] == "fail" and st["float"] == "fail" and st["catalyst"] == "fail"
    assert st["rvol"] == "unknown" and not r.in_play


@pytest.mark.asyncio
async def test_rvol_ignores_previous_days_volume(monkeypatch):
    yesterday = [Candle(t=NOW - 86400 - 60 * i, o=5, h=5.1, l=4.9, c=5, v=9_000_000) for i in range(5)]
    today = [Candle(t=NOW - 60 * i, o=5, h=5.1, l=4.9, c=5, v=100_000) for i in range(10)]
    fake = FakeMarket({"c": 5, "dp": 20}, {"shareOutstanding": 5}, {"10DayAverageTradingVolume": 1.0}, NEWS,
                      yesterday + today)
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("T", Thresholds(), include_setup=False)
    assert r.today_volume == 1_000_000 and r.rvol == 1.0


@pytest.mark.asyncio
async def test_free_plan_row_has_na_rvol_market_cap_plan_and_buy(monkeypatch):
    """No candles (free plan): RVol N/A, day-range plan from the quote, signal capped at buy."""
    quote = {"c": 5.9, "dp": 25.0, "o": 5.2, "h": 6.0, "l": 5.6, "pc": 4.72}
    fake = FakeMarket(quote, {"name": "Co", "shareOutstanding": 8.0, "marketCapitalization": 30.0},
                      {"10DayAverageTradingVolume": 1.0}, NEWS, [])
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("T", Thresholds(), include_setup=True)
    rv = next(p for p in r.pillars if p.key == "rvol")
    assert r.rvol is None and rv.status == "unknown" and rv.display == "N/A"
    assert r.market_cap == pytest.approx(5.9 * 8e6)          # live, not the profile's 30M
    assert r.plan.source == "day_range" and r.plan.entry == 6.0 and r.plan.stop == 5.6
    assert r.plan.target == 6.8 and r.plan.scale_out == 6.4 and r.plan.reward_risk == 2.0
    assert r.in_play and r.signal == "buy"
    assert "relative volume" in r.signal_note
    assert {x.factor for x in r.signal_reasons} >= {"pillars", "rvol", "momentum", "trend", "breakout", "catalyst"}


@pytest.mark.asyncio
async def test_market_cap_falls_back_to_profile(monkeypatch):
    fake = FakeMarket({"c": None, "dp": None}, {"marketCapitalization": 42.0}, {}, [], [])
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("T", Thresholds(), include_setup=False)
    assert r.market_cap == 42e6 and r.plan is None


@pytest.mark.asyncio
async def test_gap_down_is_strong_sell_without_plan(monkeypatch):
    quote = {"c": 3.0, "dp": -18.0, "o": 3.4, "h": 3.5, "l": 2.9, "pc": 3.66}
    fake = FakeMarket(quote, {"shareOutstanding": 8.0}, {}, NEWS, [])
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("T", Thresholds(), include_setup=False)
    assert r.signal == "strong_sell" and r.plan is None


@pytest.mark.asyncio
async def test_in_play_with_measured_rvol_and_setup_is_strong_buy(monkeypatch):
    # Same bull flag as the pattern test, stamped with today's times.
    from tests.test_patterns import mk
    prices = [5.0] * 15 + [5.1, 5.3, 5.5, 5.7, 5.9] + [5.85, 5.8, 5.78]
    vols = [1000] * 15 + [20000] * 5 + [4000] * 3
    candles = mk(prices, vols, t0=NOW - 60 * len(prices))
    quote = {"c": 5.8, "dp": 30.0, "o": 5.0, "h": 5.93, "l": 4.98, "pc": 4.46}
    fake = FakeMarket(quote, {"shareOutstanding": 8.0}, {"10DayAverageTradingVolume": 0.01}, NEWS, candles)
    monkeypatch.setattr(screener, "market", fake)
    r = await screener.screen_symbol("T", Thresholds(), include_setup=True)
    assert r.setup.pattern == "bull_flag"
    assert r.plan.source == "setup" and r.plan.entry == r.setup.entry and r.plan.target == r.setup.target
    assert r.signal == "strong_buy", [x.label for x in r.signal_reasons]


@pytest.mark.asyncio
async def test_http_errors_do_not_leak_the_api_key(monkeypatch):
    from app import data
    monkeypatch.setattr(data.settings, "finnhub_api_key", "SECRETKEY123")
    md = data.MarketData()
    md.http = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(403)))
    with pytest.raises(httpx.HTTPStatusError) as e:
        await md.quote("AAPL")
    assert "SECRETKEY123" not in str(e.value)
    await md.close()
