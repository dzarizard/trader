from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import yfinance as yf

from .base import DataProvider


_YF_INTERVAL_MAP = {
    "1m": "1m",
    "2m": "2m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "60m": "60m",
    "1h": "60m",
    "1d": "1d",
}


class YahooProvider(DataProvider):
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        yf_interval = _YF_INTERVAL_MAP.get(interval, interval)
        ticker = yf.Ticker(symbol)
        kwargs = {"interval": yf_interval}
        if start:
            kwargs["start"] = start
        if end:
            kwargs["end"] = end
        df: pd.DataFrame = ticker.history(**kwargs)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "ts"]).astype(
                {"open": float, "high": float, "low": float, "close": float, "volume": float}
            )
        df = df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        df = df[["open", "high", "low", "close", "volume"]]
        df.index = pd.to_datetime(df.index, utc=True)
        df["ts"] = df.index.tz_convert(timezone.utc)
        if limit and len(df) > limit:
            df = df.iloc[-limit:]
        df = df.reset_index(drop=True)
        return df

    def get_session_timezone(self, symbol: str) -> str:
        # Best effort default; could be refined per exchange
        return "America/New_York"

