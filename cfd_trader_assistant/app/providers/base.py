from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

import pandas as pd


class DataProvider(ABC):
    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Return OHLCV with columns: [open, high, low, close, volume, ts]

        - Index or column `ts` must be timezone-aware UTC
        - No missing values; forward/backfill if necessary should be avoided in providers
        """

    def get_session_timezone(self, symbol: str) -> str:
        return "UTC"

