from dataclasses import dataclass
from hashlib import sha256
from math import floor, isfinite
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OHLC = ["Open", "High", "Low", "Close"]
DEFAULT_WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "BHARTIARTL.NS", "HINDUNILVR.NS",
]


class DataError(ValueError):
    """Market data cannot be used for analysis."""


def load_symbols(path=None):
    path = Path(path) if path else ROOT / "EQUITY_L (1).csv"
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError) as exc:
        raise DataError(f"Cannot read stock universe: {path.name}") from exc
    frame.columns = frame.columns.str.strip()
    if "SYMBOL" not in frame:
        raise DataError("Stock universe must contain a SYMBOL column.")
    if "SERIES" in frame:
        frame = frame[frame["SERIES"].astype(str).str.strip().eq("EQ")]
    symbols = frame["SYMBOL"].dropna().astype(str).str.strip()
    result = sorted({f"{s}.NS" for s in symbols if s})
    if not result:
        raise DataError("Stock universe is empty.")
    return result


def add_indicators(raw, ticker=None):
    if raw is None or raw.empty:
        raise DataError("No price history returned. Check the symbol or try again later.")
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        for level in range(frame.columns.nlevels):
            if ticker in frame.columns.get_level_values(level):
                frame = frame.xs(ticker, axis=1, level=level)
                break
        if isinstance(frame.columns, pd.MultiIndex):
            raise DataError("Could not identify the requested ticker in provider data.")
    if not set(OHLC).issubset(frame.columns) or frame.columns.duplicated().any():
        raise DataError("Price history is missing unique OHLC columns.")
    frame = frame[OHLC].apply(pd.to_numeric, errors="coerce")
    frame.index = pd.to_datetime(frame.index, errors="coerce", utc=True)
    frame = frame.loc[~frame.index.isna()].sort_index()
    frame = frame.loc[~frame.index.duplicated(keep="last")]
    if frame.empty:
        raise DataError("Price history contains no valid dates.")
    valid = pd.Series(np.isfinite(frame.to_numpy()).all(axis=1), index=frame.index)
    valid &= (frame > 0).all(axis=1)
    valid &= frame["High"] >= frame[["Open", "Close", "Low"]].max(axis=1)
    valid &= frame["Low"] <= frame[["Open", "Close", "High"]].min(axis=1)
    if not valid.all():
        raise DataError("Price history contains missing or invalid OHLC candles.")
    if len(frame) < 30:
        raise DataError("At least 30 valid daily candles are required.")
    frame["EMA_9"] = frame["Close"].ewm(span=9, adjust=False).mean()
    frame["EMA_21"] = frame["Close"].ewm(span=21, adjust=False).mean()
    previous = frame["Close"].shift()
    true_range = pd.concat([
        frame["High"] - frame["Low"],
        (frame["High"] - previous).abs(),
        (frame["Low"] - previous).abs(),
    ], axis=1).max(axis=1)
    frame["ATR"] = true_range.rolling(14, min_periods=14).mean()
    return frame


@dataclass(frozen=True)
class Position:
    quantity: int
    stop: float
    risk_budget: float
    planned_risk: float
    cost: float


def size_position(price, atr, capital, risk_pct):
    if not all(isfinite(v) and v > 0 for v in (price, atr, capital, risk_pct)) or risk_pct > 100:
        raise ValueError("Price, ATR and capital must be positive; risk must be in (0, 100].")
    distance = 2 * atr
    if distance >= price:
        raise ValueError("Volatility implies a non-positive stop; no position can be sized.")
    budget = capital * risk_pct / 100
    quantity = min(floor(budget / distance), floor(capital / price))
    return Position(quantity, price - distance, budget, quantity * distance, quantity * price)


def summarize(ticker, frame, capital, risk_pct):
    last = frame.iloc[-1]
    position = size_position(float(last.Close), float(last.ATR), capital, risk_pct)
    return {
        "Symbol": ticker,
        "Candle date": frame.index[-1].strftime("%Y-%m-%d"),
        "Trend": "Bullish" if last.EMA_9 > last.EMA_21 else "Neutral / bearish",
        "Price (INR)": float(last.Close),
        "ATR (INR)": float(last.ATR),
        "Stop (INR)": position.stop,
        "Quantity": position.quantity,
        "Cost (INR)": position.cost,
        "Planned risk (INR)": position.planned_risk,
    }


def demo_history(ticker):
    """Deterministic synthetic candles, never represented as market data."""
    seed = int.from_bytes(sha256(ticker.encode()).digest()[:4], "big")
    rng = np.random.default_rng(seed)
    count = 126
    close = (100 + seed % 1900) * np.exp(np.cumsum(rng.normal(0.001, 0.012, count)))
    opening = np.r_[close[0], close[:-1]] * (1 + rng.normal(0, 0.002, count))
    spread = rng.uniform(0.004, 0.02, count)
    return pd.DataFrame({
        "Open": opening,
        "High": np.maximum(opening, close) * (1 + spread),
        "Low": np.minimum(opening, close) * (1 - spread),
        "Close": close,
    }, index=pd.bdate_range(end="2025-12-31", periods=count))
