from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .data import market
from .models import ScreenRequest, ScreenResponse, Session, StockDetail, Thresholds
from .screener import screen_many, screen_symbol
from .session import market_session

UNIVERSE_FILE = Path(__file__).resolve().parent.parent / "universe.txt"
MAX_SYMBOLS = 40  # 4 Finnhub calls per symbol, 60 calls/min on the free plan


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await market.close()


app = FastAPI(title="Momentum Screener", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_universe() -> list[str]:
    if not UNIVERSE_FILE.exists():
        return []
    return [
        line.strip().upper()
        for line in UNIVERSE_FILE.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/docs")


@app.get("/api/health")
async def health():
    """Also validates the key with one live quote so the UI can say 'connected'."""
    key_set = bool(settings.finnhub_api_key) and "paste_your" not in settings.finnhub_api_key
    finnhub_ok, finnhub_error = False, None
    if key_set:
        try:
            q = await market.quote("AAPL")
            finnhub_ok = bool(q.get("c"))
            if not finnhub_ok:
                finnhub_error = "Finnhub answered but returned no price — check the key"
        except Exception as e:
            finnhub_error = str(e)
    return {
        "ok": True,
        "finnhub_key_set": key_set,
        "finnhub_ok": finnhub_ok,
        "finnhub_error": finnhub_error,
        "candles_available": not market.candles_blocked,
        "session": market_session(),
    }


@app.get("/api/session", response_model=Session)
async def session():
    return market_session()


@app.get("/api/universe")
async def universe():
    return {"symbols": load_universe()}


@app.get("/api/thresholds", response_model=Thresholds)
async def thresholds():
    return Thresholds()


@app.post("/api/screen", response_model=ScreenResponse)
async def screen(req: ScreenRequest):
    symbols = list(dict.fromkeys(s.upper().strip() for s in req.symbols if s.strip())) or load_universe()
    if not symbols:
        raise HTTPException(400, "Nothing to scan. Paste tickers in the box or add them to backend/universe.txt.")
    symbols = symbols[:MAX_SYMBOLS]
    results = await screen_many(symbols, req.thresholds, req.include_setups)
    in_play = [r.symbol for r in results if r.in_play][:10]
    return ScreenResponse(
        scanned_at=datetime.now(timezone.utc).isoformat(),
        session=market_session(),
        candles_available=not market.candles_blocked,
        thresholds=req.thresholds,
        results=results,
        in_play=in_play,
    )


@app.get("/api/stock/{symbol}", response_model=StockDetail)
async def stock(symbol: str):
    result = await screen_symbol(symbol, Thresholds(), include_setup=True)
    if result.error:
        raise HTTPException(502, result.error)
    candles = await market.candles_1m(symbol.upper())
    news = await market.news(symbol.upper(), 48)
    return StockDetail(result=result, candles=candles[-120:], news=news[:10])
