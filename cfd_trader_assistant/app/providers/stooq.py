from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

from .base import DataProvider


class StooqProvider(DataProvider):
    """Simple EOD provider using Stooq CSV endpoint.

    Stooq symbols examples:
    - SPY.US
    - QQQ.US
    - ^NDX
    """

    BASE = "https://stooq.com/q/d/l/"

    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        # Only EOD supported
        params = {"s": symbol, "i": "d"}
        resp = requests.get(self.BASE, params=params, timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(pd.compat.StringIO(resp.text))
        df = df.rename(columns={
            "Date": "ts",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })
        df["ts"] = pd.to_datetime(df["ts"], utc=True)
        df = df[["open", "high", "low", "close", "volume", "ts"]]
        if limit and len(df) > limit:
            df = df.iloc[-limit:]
        df = df.reset_index(drop=True)
        return df

    def get_session_timezone(self, symbol: str) -> str:
        return "America/New_York"

