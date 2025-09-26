"""
Stooq data provider for CFD Trader Assistant.
Provides EOD (End of Day) data for free.
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging
from .base import DataProvider

logger = logging.getLogger(__name__)


class StooqProvider(DataProvider):
    """Stooq data provider implementation for EOD data."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = "https://stooq.com/q/d/l/"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'CFD-Trader-Assistant/1.0'
        })
    
    def get_supported_intervals(self) -> list[str]:
        """Get list of supported time intervals (EOD only)."""
        return ["1d"]
    
    def get_ohlcv(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get EOD OHLCV data from Stooq with UTC timestamps.
        
        Args:
            symbol: Trading symbol
            interval: Time interval (only '1d' supported)
            start: Start datetime in UTC (optional)
            end: End datetime in UTC (optional)
            
        Returns:
            DataFrame with OHLCV data and UTC timestamps
        """
        if interval != "1d":
            logger.warning(f"Stooq provider only supports daily data, requested: {interval}")
            return pd.DataFrame()
        
        try:
            # Map symbol to Stooq format
            stooq_symbol = self._map_symbol(symbol)
            
            # Build URL
            url = f"{self.base_url}s={stooq_symbol}&i=d"
            
            # Add date range if specified
            if start:
                url += f"&d1={start.strftime('%Y%m%d')}"
            if end:
                url += f"&d2={end.strftime('%Y%m%d')}"
            
            # Fetch data
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV data
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return pd.DataFrame()
            
            # Standardize column names
            df = df.rename(columns={
                'Date': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Convert timestamp to datetime (Stooq returns UTC dates)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            # Sort by timestamp (ascending)
            df = df.sort_values('timestamp')
            
            # Ensure proper data types
            for col in ['open', 'high', 'low', 'close']:
                df[col] = df[col].astype(float)
            
            if 'volume' in df.columns:
                df['volume'] = df['volume'].astype(float)
            
            # Validate and ensure UTC timestamps
            df = self._validate_ohlcv_data(df)
            
            logger.debug(f"Retrieved {len(df)} EOD bars for {symbol}")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Stooq data for {symbol}: {e}")
            return pd.DataFrame()
    
    def get_session_info(self, symbol: str) -> Dict[str, Any]:
        """Get trading session information."""
        return {
            'timezone': 'UTC',
            'exchange': 'Stooq',
            'currency': 'USD',
            'market_state': 'EOD_ONLY',
            'data_type': 'End of Day'
        }
    
    def is_market_open(self, symbol: str) -> bool:
        """Stooq provides EOD data only, so market is always 'closed' for real-time purposes."""
        return False
    
    def _map_symbol(self, symbol: str) -> str:
        """Map our symbol format to Stooq format."""
        # Common symbol mappings
        mapping = {
            'SPY': 'spy',
            'QQQ': 'qqq',
            'IWM': 'iwm',
            'GLD': 'gld',
            'SLV': 'slv',
            'TLT': 'tlt',
            'VTI': 'vti',
            'VEA': 'vea',
            'VWO': 'vwo',
            'BND': 'bnd',
            'AGG': 'agg',
            'LQD': 'lqd',
            'HYG': 'hyg',
            'EMB': 'emb',
            'EFA': 'efa',
            'EEM': 'eem',
            'FXI': 'fxi',
            'EWJ': 'ewj',
            'EWZ': 'ewz',
            'EWY': 'ewy',
            'EWT': 'ewt',
            'EWH': 'ewh',
            'EWS': 'ews',
            'EWA': 'ewa',
            'EWC': 'ewc',
            'EWG': 'ewg',
            'EWU': 'ewu',
            'EWL': 'ewl',
            'EWI': 'ewi',
            'EWP': 'ewp',
            'EWQ': 'ewq',
            'EWN': 'ewn',
            'EWO': 'ewo',
            'EWK': 'ewk',
            'EWD': 'ewd',
            'EWM': 'ewm',
            'EZA': 'eza',
            'EIS': 'eis',
            'EIDO': 'eido',
            'EIRL': 'eirl',
            'EIS': 'eis',
            'EIDO': 'eido',
            'EIRL': 'eirl'
        }
        
        # If symbol is in mapping, use it
        if symbol.upper() in mapping:
            return mapping[symbol.upper()]
        
        # For indices, try common patterns
        if symbol.startswith('^'):
            return symbol[1:].lower()
        
        # For forex, convert format
        if 'USD' in symbol or 'EUR' in symbol or 'GBP' in symbol:
            return symbol.replace('=', '').lower()
        
        # Default: convert to lowercase
        return symbol.lower()
    
    def get_available_symbols(self) -> list[str]:
        """Get list of available symbols (limited implementation)."""
        # This would require scraping or API documentation
        # For now, return common symbols
        return [
            'SPY', 'QQQ', 'IWM', 'GLD', 'SLV', 'TLT',
            'VTI', 'VEA', 'VWO', 'BND', 'AGG', 'LQD',
            'HYG', 'EMB', 'EFA', 'EEM', 'FXI', 'EWJ'
        ]