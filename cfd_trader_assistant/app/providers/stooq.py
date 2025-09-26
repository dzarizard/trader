from __future__ import annotations

import io
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProvider


def _map_symbol(sym: str) -> str:
    s = sym.lower().replace("^", "")
    return s


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8))
def _download_csv(sym: str) -> pd.DataFrame:
    url = f"https://stooq.pl/q/d/l/?s={sym}&i=d"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    return df


class StooqProvider(DataProvider):
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        mapped = _map_symbol(symbol)
        df = _download_csv(mapped)
        df.rename(
            columns={"Date": "ts", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"},
            inplace=True,
        )
        if "ts" not in df:
            df.rename(columns={"date": "ts", "open": "open", "high": "high", "low": "low", "close": "close", "volume": "volume"}, inplace=True)
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df[["ts", "open", "high", "low", "close", "volume"]].dropna()
        return df.tail(limit)

