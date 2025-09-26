"""
Utility functions for CFD Trader Assistant.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Setup logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_format: Log format (json, text)
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format
    if log_format == "json":
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Setup file handler
    file_handler = logging.FileHandler(
        log_dir / f"cfd_trader_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setFormatter(formatter)
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logging.error(f"Error loading config from {config_path}: {e}")
        return {}


def save_config(config: Dict[str, Any], config_path: str) -> bool:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to configuration file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import yaml
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"Error saving config to {config_path}: {e}")
        return False


def get_market_timezone(symbol: str) -> str:
    """
    Get market timezone for a symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Timezone string
    """
    # Common market timezones
    timezone_map = {
        'SPY': 'America/New_York',
        'QQQ': 'America/New_York',
        'NAS100': 'America/New_York',
        'SPX500': 'America/New_York',
        'DAX40': 'Europe/Berlin',
        'FTSE100': 'Europe/London',
        'EURUSD': 'UTC',
        'GBPUSD': 'UTC',
        'USDJPY': 'UTC',
        'GOLD': 'UTC',
        'OIL': 'UTC'
    }
    
    return timezone_map.get(symbol, 'UTC')


def is_market_hours(symbol: str, current_time: Optional[datetime] = None) -> bool:
    """
    Check if market is open for a symbol.
    
    Args:
        symbol: Trading symbol
        current_time: Time to check (defaults to now)
        
    Returns:
        True if market is open
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Simple market hours check (can be enhanced)
    market_hours = {
        'SPY': {'start': '09:30', 'end': '16:00', 'timezone': 'America/New_York'},
        'QQQ': {'start': '09:30', 'end': '16:00', 'timezone': 'America/New_York'},
        'NAS100': {'start': '09:30', 'end': '16:00', 'timezone': 'America/New_York'},
        'SPX500': {'start': '09:30', 'end': '16:00', 'timezone': 'America/New_York'},
        'DAX40': {'start': '09:00', 'end': '17:30', 'timezone': 'Europe/Berlin'},
        'FTSE100': {'start': '08:00', 'end': '16:30', 'timezone': 'Europe/London'},
        'EURUSD': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'},
        'GBPUSD': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'},
        'USDJPY': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'},
        'GOLD': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'},
        'OIL': {'start': '00:00', 'end': '23:59', 'timezone': 'UTC'}
    }
    
    if symbol not in market_hours:
        return True  # Default to open if unknown
    
    hours = market_hours[symbol]
    
    # Convert to market timezone (simplified)
    # In production, use pytz or zoneinfo for proper timezone handling
    current_hour = current_time.hour
    current_minute = current_time.minute
    current_time_str = f"{current_hour:02d}:{current_minute:02d}"
    
    return hours['start'] <= current_time_str <= hours['end']


def calculate_pips(entry_price: float, exit_price: float, symbol: str) -> float:
    """
    Calculate pip distance between two prices.
    
    Args:
        entry_price: Entry price
        exit_price: Exit price
        symbol: Trading symbol
        
    Returns:
        Pip distance
    """
    if 'USD' in symbol or 'EUR' in symbol or 'GBP' in symbol:
        # Forex pairs - 4 decimal places
        return abs(exit_price - entry_price) / 0.0001
    else:
        # Indices and commodities - 1 decimal place
        return abs(exit_price - entry_price) / 0.1


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount.
    
    Args:
        amount: Amount to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "GBP":
        return f"£{amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage value.
    
    Args:
        value: Value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0, *args, **kwargs):
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds
        *args: Function arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        Exception: If all retries fail
    """
    for attempt in range(max_retries + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            delay = base_delay * (2 ** attempt)
            logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ValueError):
        return default


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """
    Calculate Sharpe ratio.
    
    Args:
        returns: Series of returns
        risk_free_rate: Risk-free rate (annual)
        
    Returns:
        Sharpe ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    
    excess_returns = returns.mean() - (risk_free_rate / 252)  # Daily risk-free rate
    return excess_returns / returns.std() * np.sqrt(252)


def calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """
    Calculate maximum drawdown.
    
    Args:
        equity_curve: Series of equity values
        
    Returns:
        Maximum drawdown as percentage
    """
    if len(equity_curve) == 0:
        return 0.0
    
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak * 100
    return drawdown.min()


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """
    Calculate Compound Annual Growth Rate.
    
    Args:
        start_value: Starting value
        end_value: Ending value
        years: Number of years
        
    Returns:
        CAGR as percentage
    """
    if start_value <= 0 or years <= 0:
        return 0.0
    
    return (end_value / start_value) ** (1 / years) - 1


def validate_price(price: float, symbol: str) -> bool:
    """
    Validate price for a symbol.
    
    Args:
        price: Price to validate
        symbol: Trading symbol
        
    Returns:
        True if price is valid
    """
    if price <= 0 or not isinstance(price, (int, float)):
        return False
    
    # Symbol-specific validation
    if 'USD' in symbol:
        # Forex pairs should be in reasonable range
        return 0.5 <= price <= 2.0
    elif 'NAS' in symbol or 'SPX' in symbol:
        # Indices should be in reasonable range
        return 1000 <= price <= 50000
    elif 'GOLD' in symbol:
        # Gold should be in reasonable range
        return 1000 <= price <= 3000
    
    return True


def clean_symbol(symbol: str) -> str:
    """
    Clean and normalize symbol name.
    
    Args:
        symbol: Raw symbol
        
    Returns:
        Cleaned symbol
    """
    # Remove common suffixes and prefixes
    symbol = symbol.replace('^', '').replace('=', '').replace('X', '')
    
    # Convert to uppercase
    symbol = symbol.upper()
    
    # Handle common variations
    symbol_map = {
        'NDX': 'NAS100',
        'GSPC': 'SPX500',
        'GDAXI': 'DAX40',
        'FTSE': 'FTSE100'
    }
    
    return symbol_map.get(symbol, symbol)


def get_instrument_type(symbol: str) -> str:
    """
    Determine instrument type from symbol.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        Instrument type (fx, index, commodity, stock)
    """
    if any(currency in symbol for currency in ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD']):
        return 'fx'
    elif any(index in symbol for index in ['SPX', 'NAS', 'DAX', 'FTSE', 'NIKKEI']):
        return 'index'
    elif any(commodity in symbol for commodity in ['GOLD', 'SILVER', 'OIL', 'COPPER']):
        return 'commodity'
    else:
        return 'stock'


def create_sample_data(symbol: str, days: int = 30, interval: str = '1D') -> pd.DataFrame:
    """
    Create sample data for testing.
    
    Args:
        symbol: Trading symbol
        days: Number of days
        interval: Data interval
        
    Returns:
        Sample DataFrame
    """
    dates = pd.date_range(start=datetime.now() - pd.Timedelta(days=days), end=datetime.now(), freq=interval)
    
    # Generate realistic price data
    np.random.seed(42)
    base_price = 18500 if 'NAS' in symbol else 1.0850 if 'USD' in symbol else 100
    
    returns = np.random.normal(0, 0.02, len(dates))
    prices = [base_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    data = []
    for i, (date, price) in enumerate(zip(dates, prices)):
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'timestamp': date,
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data)


def save_json(data: Dict[str, Any], filepath: str) -> bool:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        filepath: File path
        
    Returns:
        True if successful
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logging.error(f"Error saving JSON to {filepath}: {e}")
        return False


def load_json(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file.
    
    Args:
        filepath: File path
        
    Returns:
        Loaded data or None
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading JSON from {filepath}: {e}")
        return None


def ensure_directory(path: str) -> None:
    """
    Ensure directory exists.
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def get_file_size_mb(filepath: str) -> float:
    """
    Get file size in MB.
    
    Args:
        filepath: File path
        
    Returns:
        File size in MB
    """
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except OSError:
        return 0.0


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."