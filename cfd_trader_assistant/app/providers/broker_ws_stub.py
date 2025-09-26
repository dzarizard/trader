from __future__ import annotations

"""
BrokerWebsocketProvider skeleton
--------------------------------

This is a placeholder for integrating a real-time broker websocket feed.

Expected responsibilities:
- Authenticate and connect to broker's WS API
- Subscribe/unsubscribe to symbols and intervals
- Collect ticks/bars and aggregate to OHLCV (1m/5m)
- Provide a `get_ohlcv` compatible cache for recent history

How to implement:
1. Use the broker's Python SDK or `websockets`/`aiohttp` to connect
2. Maintain an in-memory store per symbol with latest N bars
3. On `get_ohlcv`, merge cached bars with historical REST for continuity
4. Ensure timestamps are timezone-aware (UTC)
5. Add reconnection with exponential backoff

Note: For this MVP, real-time is disabled. Use Yahoo/Stooq providers.
"""

from typing import Optional
from datetime import datetime
import pandas as pd

from .base import DataProvider


class BrokerWebsocketProvider(DataProvider):
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        raise NotImplementedError("Real-time provider not implemented in MVP")

