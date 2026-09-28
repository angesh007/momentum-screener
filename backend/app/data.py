"""Market data access — Finnhub only.

Free tier (60 req/min) covers quote, company profile, basic metrics and
company news for US stocks. Intraday candles (/stock/candle) need a paid plan;
on the free plan the call returns 403 and this client returns an empty list,
which the screener reports as "relative volume / setup unavailable".
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from .config import settings
from .models import Candle, NewsItem

FINNHUB = "https://finnhub.io/api/v1"


class RateLimiter:
    """Token bucket sized for Finnhub's free plan."""

    def __init__(self, per_minute: int = 55):
        self.capacity = per_minute
        self.tokens = float(per_minute)
        self.refill = per_minute / 60.0
        self.last = time.monotonic()
        self.lock = asyncio.Lock()

    async def take(self):
        async with self.lock:
            now = time.monotonic()
            self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.refill)
            self.last = now
            if self.tokens < 1:
                await asyncio.sleep((1 - self.tokens) / self.refill)
                self.tokens = 0
            else:
                self.tokens -= 1


class TTLCache:
    def __init__(self):
        self._d: dict[str, tuple[float, Any]] = {}

    def get(self, key: str):
        hit = self._d.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        return None

    def set(self, key: str, value: Any, ttl: float):
        self._d[key] = (time.monotonic() + ttl, value)


class MarketData:
    def __init__(self):
        self.limiter = RateLimiter()
        self.cache = TTLCache()
        self.http = httpx.AsyncClient(timeout=15)
        self.candles_blocked = False  # set once Finnhub says candles are premium

    async def _get(self, path: str, ttl: float, **params) -> Any:
        key = path + str(sorted(params.items()))
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        if not settings.finnhub_api_key:
            raise RuntimeError("FINNHUB_API_KEY is not set")
        await self.limiter.take()
        r = await self.http.get(
            f"{FINNHUB}{path}", params={**params, "token": settings.finnhub_api_key}
        )
        if r.status_code == 429:
            await asyncio.sleep(2)
            return await self._get(path, ttl, **params)
        if r.is_error:
            # httpx's default message embeds the request URL, including ?token=<key>.
            # These strings reach the browser (row errors, /api/health), so keep them key-free.
            raise httpx.HTTPStatusError(
                f"Finnhub {path} returned HTTP {r.status_code}", request=r.request, response=r
            )
        data = r.json()
        self.cache.set(key, data, ttl)
        return data

    # ---- Finnhub (free) ----------------------------------------------------

    async def quote(self, symbol: str) -> dict:
        return await self._get("/quote", ttl=20, symbol=symbol)

    async def profile(self, symbol: str) -> dict:
        return await self._get("/stock/profile2", ttl=3600, symbol=symbol)

    async def metrics(self, symbol: str) -> dict:
        d = await self._get("/stock/metric", ttl=3600, symbol=symbol, metric="all")
        return d.get("metric", {}) or {}

    async def news(self, symbol: str, hours: int) -> list[NewsItem]:
        now = datetime.now(timezone.utc)
        frm = (now - timedelta(hours=max(hours, 24))).date().isoformat()
        raw = await self._get(
            "/company-news", ttl=300, symbol=symbol, **{"from": frm, "to": now.date().isoformat()}
        )
        cutoff = now - timedelta(hours=hours)
        items = []
        for n in raw or []:
            ts = datetime.fromtimestamp(n.get("datetime", 0), tz=timezone.utc)
            if ts >= cutoff:
                items.append(
                    NewsItem(
                        headline=n.get("headline", ""),
                        source=n.get("source", ""),
                        url=n.get("url", ""),
                        published=ts.isoformat(),
                    )
                )
        return items

    # ---- Candles (paid plan only) -------------------------------------------

    async def candles_1m(self, symbol: str) -> list[Candle]:
        if self.candles_blocked:
            return []
        to = int(time.time())
        frm = to - 60 * 60 * 8
        try:
            d = await self._get("/stock/candle", ttl=30, symbol=symbol, resolution="1", **{"from": frm, "to": to})
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                self.candles_blocked = True
                return []
            raise
        if d.get("s") != "ok":
            return []
        return [
            Candle(t=t, o=o, h=h, l=l, c=c, v=v)
            for t, o, h, l, c, v in zip(d["t"], d["o"], d["h"], d["l"], d["c"], d["v"])
        ]

    async def close(self):
        await self.http.aclose()


market = MarketData()
