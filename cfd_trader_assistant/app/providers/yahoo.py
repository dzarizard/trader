from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import DataProvider


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=8))
def _fetch_chart(symbol: str, interval: str, rng: str) -> dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"interval": interval, "range": rng}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


class YahooProvider(DataProvider):
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        # Determine range from interval and limit
        interval = interval.lower()
        if interval in {"1m", "2m", "5m", "15m", "30m", "60m", "90m"}:
            rng = "5d"
        elif interval in {"1h"}:
            rng = "1mo"
            interval = "60m"
        elif interval in {"1d"}:
            rng = "10y"
        else:
            rng = "1mo"

        data = _fetch_chart(symbol, interval, rng)
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        indicators = result["indicators"]["quote"][0]
        volume = indicators.get("volume", [None] * len(timestamps))
        rows = []
        for i, ts in enumerate(timestamps[-limit:]):
            ts_dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            rows.append(
                {
                    "ts": ts_dt,
                    "open": indicators["open"][i],
                    "high": indicators["high"][i],
                    "low": indicators["low"][i],
                    "close": indicators["close"][i],
                    "volume": volume[i] if volume else None,
                }
            )
        df = pd.DataFrame(rows).dropna()
        return df

