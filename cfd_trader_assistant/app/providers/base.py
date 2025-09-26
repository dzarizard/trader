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
        """Return OHLCV dataframe with columns: open, high, low, close, volume, ts (UTC)."""
        raise NotImplementedError

