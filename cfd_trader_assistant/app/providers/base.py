"""
Base data provider interface for CFD Trader Assistant.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class OHLCVData(BaseModel):
    """Standardized OHLCV data structure."""
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: datetime


class DataProvider(ABC):
    """Abstract base class for data providers with standardized UTC interface."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
        self._cache = {}
        self._cache_ttl = 60  # Cache TTL in seconds
    
    @abstractmethod
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol with standardized UTC timestamps.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (1m, 5m, 15m, 1h, 1d, etc.)
            start: Start datetime in UTC (optional)
            end: End datetime in UTC (optional)
            
        Returns:
            DataFrame with columns: timestamp (UTC), open, high, low, close, volume
            All timestamps must be in UTC timezone
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
            end = datetime.now()
            start = end - timedelta(minutes=5)
            df = self.get_ohlcv(symbol, "1m", start=start, end=end)
            if not df.empty:
                return float(df.iloc[-1]['close'])
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {e}")
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
            DataFrame with historical OHLCV data in UTC
        """
        end = datetime.now()
        start = end - timedelta(days=days)
        return self.get_ohlcv(symbol, interval, start=start, end=end)
    
    def _ensure_utc_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ensure all timestamps are in UTC timezone.
        
        Args:
            df: DataFrame with timestamp column
            
        Returns:
            DataFrame with UTC timestamps
        """
        if df.empty:
            return df
        
        if 'timestamp' in df.columns:
            # Convert to UTC if timezone-aware
            if hasattr(df['timestamp'].dtype, 'tz') and df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC')
            else:
                # Assume naive timestamps are in UTC
                df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        
        return df
    
    def _validate_ohlcv_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean OHLCV data.
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Ensure required columns exist
        required_cols = ['timestamp', 'open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Ensure UTC timestamps
        df = self._ensure_utc_timestamps(df)
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        # Validate OHLC relationships
        invalid_rows = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | (df['low'] > df['open']) | (df['low'] > df['close'])
        if invalid_rows.any():
            logger.warning(f"Found {invalid_rows.sum()} invalid OHLC rows, removing them")
            df = df[~invalid_rows]
        
        # Ensure numeric types
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remove rows with NaN values
        df = df.dropna()
        
        return df