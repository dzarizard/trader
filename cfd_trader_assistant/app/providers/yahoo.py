"""
Yahoo Finance data provider for CFD Trader Assistant.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from .base import DataProvider

logger = logging.getLogger(__name__)


class YahooProvider(DataProvider):
    """Yahoo Finance data provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get('api_key')
        self.session = None
    
    def get_supported_intervals(self) -> list[str]:
        """Get list of supported time intervals."""
        return ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
    
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get OHLCV data from Yahoo Finance.
        
        Args:
            symbol: Trading symbol
            interval: Time interval
            limit: Maximum number of bars to return
            start: Start datetime (optional)
            end: End datetime (optional)
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Map interval to yfinance format
            yf_interval = self._map_interval(interval)
            
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Determine period based on interval and limit
            if start and end:
                period = None
            else:
                period = self._get_period_for_limit(limit, interval)
                start = None
                end = None
            
            # Fetch data
            df = ticker.history(
                period=period,
                interval=yf_interval,
                start=start,
                end=end,
                auto_adjust=True,
                prepost=True,
                threads=True
            )
            
            if df.empty:
                logger.warning(f"No data returned for {symbol} with interval {interval}")
                return pd.DataFrame()
            
            # Standardize column names and add timestamp
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add timestamp column
            df['timestamp'] = df.index
            
            # Reset index to make timestamp a regular column
            df = df.reset_index(drop=True)
            
            # Limit results if needed
            if limit and len(df) > limit:
                df = df.tail(limit)
            
            # Ensure proper data types
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            if 'volume' in df.columns:
                df['volume'] = df['volume'].astype(float)
            
            logger.debug(f"Retrieved {len(df)} bars for {symbol} {interval}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_session_info(self, symbol: str) -> Dict[str, Any]:
        """Get trading session information."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                'timezone': info.get('exchangeTimezoneName', 'UTC'),
                'exchange': info.get('exchange', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'market_state': info.get('marketState', 'UNKNOWN'),
                'regular_market_time': info.get('regularMarketTime'),
                'pre_market_time': info.get('preMarketTime'),
                'post_market_time': info.get('postMarketTime')
            }
        except Exception as e:
            logger.error(f"Error getting session info for {symbol}: {e}")
            return {}
    
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is currently open."""
        try:
            session_info = self.get_session_info(symbol)
            market_state = session_info.get('market_state', 'UNKNOWN')
            return market_state in ['REGULAR', 'PRE', 'POST']
        except Exception as e:
            logger.error(f"Error checking market status for {symbol}: {e}")
            return False
    
    def _map_interval(self, interval: str) -> str:
        """Map our interval format to yfinance format."""
        mapping = {
            '1m': '1m',
            '2m': '2m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '60m': '60m',
            '1h': '1h',
            '1d': '1d',
            '1wk': '1wk',
            '1mo': '1mo'
        }
        return mapping.get(interval, '1d')
    
    def _get_period_for_limit(self, limit: int, interval: str) -> str:
        """Determine appropriate period based on limit and interval."""
        # Estimate days needed based on interval and limit
        interval_minutes = self._interval_to_minutes(interval)
        total_minutes = limit * interval_minutes
        days = max(1, total_minutes // (24 * 60) + 1)
        
        if days <= 7:
            return "7d"
        elif days <= 30:
            return "1mo"
        elif days <= 90:
            return "3mo"
        elif days <= 365:
            return "1y"
        else:
            return "max"
    
    def _interval_to_minutes(self, interval: str) -> int:
        """Convert interval string to minutes."""
        mapping = {
            '1m': 1,
            '2m': 2,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '60m': 60,
            '1h': 60,
            '1d': 24 * 60,
            '1wk': 7 * 24 * 60,
            '1mo': 30 * 24 * 60
        }
        return mapping.get(interval, 60)
    
    def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """Get additional ticker information."""
        try:
            ticker = yf.Ticker(symbol)
            return ticker.info
        except Exception as e:
            logger.error(f"Error getting ticker info for {symbol}: {e}")
            return {}