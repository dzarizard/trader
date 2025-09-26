"""
Base data provider interface for CFD Trader Assistant.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
from pydantic import BaseModel


class OHLCVData(BaseModel):
    """Standardized OHLCV data structure."""
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: datetime


class DataProvider(ABC):
    """Abstract base class for data providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (1m, 5m, 15m, 1h, 1d, etc.)
            limit: Maximum number of bars to return
            start: Start datetime (optional)
            end: End datetime (optional)
            
        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
        """
        pass
    
    @abstractmethod
    def get_session_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get trading session information for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dictionary with session info (timezone, hours, etc.)
        """
        pass
    
    @abstractmethod
    def is_market_open(self, symbol: str) -> bool:
        """
        Check if market is currently open for the symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if market is open, False otherwise
        """
        pass
    
    def validate_interval(self, interval: str) -> bool:
        """Validate if the provider supports the given interval."""
        supported_intervals = self.get_supported_intervals()
        return interval in supported_intervals
    
    @abstractmethod
    def get_supported_intervals(self) -> list[str]:
        """Get list of supported time intervals."""
        pass
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get the latest price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest close price or None if unavailable
        """
        try:
            df = self.get_ohlcv(symbol, "1m", limit=1)
            if not df.empty:
                return float(df.iloc[-1]['close'])
        except Exception:
            pass
        return None
    
    def get_historical_data(
        self,
        symbol: str,
        interval: str,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Get historical data for the specified number of days.
        
        Args:
            symbol: Trading symbol
            interval: Time interval
            days: Number of days to fetch
            
        Returns:
            DataFrame with historical OHLCV data
        """
        end = datetime.now()
        start = end - timedelta(days=days)
        return self.get_ohlcv(symbol, interval, start=start, end=end)