from typing import Literal, Optional
from pydantic import BaseModel, Field

PillarStatus = Literal["pass", "fail", "warn", "unknown"]


class Thresholds(BaseModel):
    price_min: float = 2.0
    price_max: float = 20.0
    gap_pct_min: float = 10.0
    rvol_min: float = 5.0
    float_ideal: float = 10_000_000
    float_max: float = 100_000_000
    news_lookback_hours: int = 24


class Pillar(BaseModel):
    key: str
    label: str
    status: PillarStatus
    value: Optional[float] = None
    display: str = ""
    note: str = ""


class NewsItem(BaseModel):
    headline: str
    source: str
    url: str
    published: str


class Candle(BaseModel):
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float


class Setup(BaseModel):
    pattern: Literal["bull_flag", "flat_top", "none"]
    stage: str
    entry: Optional[float] = None
    stop: Optional[float] = None
    scale_out: Optional[float] = None   # sell half here (+1R), move stop to entry
    target: Optional[float] = None      # +2R on the remaining half
    risk: Optional[float] = None
    reward_risk: Optional[float] = None
    ema9: Optional[float] = None
    notes: list[str] = Field(default_factory=list)


class ScreenResult(BaseModel):
    symbol: str
    name: str = ""
    price: Optional[float] = None
    gap_pct: Optional[float] = None
    rvol: Optional[float] = None
    today_volume: Optional[float] = None
    avg_volume: Optional[float] = None
    shares_outstanding: Optional[float] = None
    pillars: list[Pillar]
    score: int
    in_play: bool
    catalyst: Optional[NewsItem] = None
    news_count: int = 0
    setup: Optional[Setup] = None
    error: Optional[str] = None


class ScreenRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)  # empty = use universe.txt
    thresholds: Thresholds = Field(default_factory=Thresholds)
    include_setups: bool = True


class Session(BaseModel):
    et_time: str
    et_date: str
    phase: str
    tradeable: bool
    advice: str


class ScreenResponse(BaseModel):
    scanned_at: str
    session: Session
    candles_available: bool      # False on the Finnhub free plan
    thresholds: Thresholds
    results: list[ScreenResult]
    in_play: list[str]           # capped at 10 — Ross trades 5–10 stocks in play


class StockDetail(BaseModel):
    result: ScreenResult
    candles: list[Candle]
    news: list[NewsItem]
