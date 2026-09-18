import pytest

from app import screener
from app.models import Candle, Thresholds


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
    candles = [Candle(t=i, o=5, h=5.1, l=4.9, c=5, v=500_000) for i in range(20)]
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
