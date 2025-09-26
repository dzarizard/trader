from __future__ import annotations

"""
Skeleton for integrating a real-time broker WebSocket feed.

How to implement:
- Connect to broker's WS using their SDK or websockets library
- Authenticate with API key/secret if required
- Subscribe to symbol candles or trades and aggregate to desired interval
- Maintain an in-memory buffer per symbol/interval and flush into pandas DataFrame
- Expose a non-blocking method to retrieve the last N bars for strategy

Security and reliability:
- Implement exponential backoff reconnects
- Heartbeat and ping/pong
- Timeouts and message validation
"""

from typing import Optional
import pandas as pd

from .base import DataProvider


class BrokerWebsocketProvider(DataProvider):
    def __init__(self) -> None:
        pass

    def get_ohlcv(self, symbol: str, interval: str, limit: int, start=None, end=None) -> pd.DataFrame:  # type: ignore[override]
        raise NotImplementedError("Real-time WS provider is a stub. Implement broker integration.")

