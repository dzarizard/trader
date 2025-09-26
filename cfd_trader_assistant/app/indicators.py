"""
Technical indicators for CFD Trader Assistant.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def compute_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """
    Compute all technical indicators for the given DataFrame.
    
    Args:
        df: DataFrame with OHLCV data
        config: Configuration dictionary with indicator parameters
        
    Returns:
        Dictionary with indicator names as keys and Series as values
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to compute_indicators")
        return {}
    
    indicators = {}
    
    try:
        # Trend indicators
        indicators.update(compute_trend_indicators(df, config))
        
        # Momentum indicators
        indicators.update(compute_momentum_indicators(df, config))
        
        # Volatility indicators
        indicators.update(compute_volatility_indicators(df, config))
        
        # Volume indicators
        indicators.update(compute_volume_indicators(df, config))
        
        # Support/Resistance indicators
        indicators.update(compute_support_resistance_indicators(df, config))
        
        logger.debug(f"Computed {len(indicators)} indicators")
        return indicators
        
    except Exception as e:
        logger.error(f"Error computing indicators: {e}")
        return {}


def compute_trend_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """Compute trend-following indicators."""
    indicators = {}
    
    try:
        # Simple Moving Averages
        sma_fast = config.get('trend', {}).get('sma_fast', 20)
        sma_mid = config.get('trend', {}).get('sma_mid', 50)
        sma_long = config.get('trend', {}).get('sma_long', 200)
        
        indicators['sma_20'] = sma(df['close'], sma_fast)
        indicators['sma_50'] = sma(df['close'], sma_mid)
        indicators['sma_200'] = sma(df['close'], sma_long)
        
        # Exponential Moving Averages
        indicators['ema_12'] = ema(df['close'], 12)
        indicators['ema_26'] = ema(df['close'], 26)
        
        # MACD
        macd_fast = config.get('entry', {}).get('macd_fast', 12)
        macd_slow = config.get('entry', {}).get('macd_slow', 26)
        macd_signal = config.get('entry', {}).get('macd_signal', 9)
        
        macd_line, signal_line, histogram = macd(df['close'], macd_fast, macd_slow, macd_signal)
        indicators['macd'] = macd_line
        indicators['macd_signal'] = signal_line
        indicators['macd_histogram'] = histogram
        
    except Exception as e:
        logger.error(f"Error computing trend indicators: {e}")
    
    return indicators


def compute_momentum_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """Compute momentum indicators."""
    indicators = {}
    
    try:
        # Rate of Change
        roc_lookback = config.get('entry', {}).get('roc_lookback', 10)
        indicators['roc'] = roc(df['close'], roc_lookback)
        
        # RSI
        indicators['rsi'] = rsi(df['close'], 14)
        
        # Stochastic Oscillator
        k_percent, d_percent = stoch(df['high'], df['low'], df['close'], 14, 3)
        indicators['stoch_k'] = k_percent
        indicators['stoch_d'] = d_percent
        
        # Williams %R
        indicators['williams_r'] = williams_r(df['high'], df['low'], df['close'], 14)
        
    except Exception as e:
        logger.error(f"Error computing momentum indicators: {e}")
    
    return indicators


def compute_volatility_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """Compute volatility indicators."""
    indicators = {}
    
    try:
        # Average True Range
        atr_period = config.get('quality', {}).get('atr_period', 14)
        indicators['atr'] = atr(df['high'], df['low'], df['close'], atr_period)
        
        # Bollinger Bands
        bb_period = 20
        bb_std = 2
        upper, middle, lower = bollinger_bands(df['close'], bb_period, bb_std)
        indicators['bb_upper'] = upper
        indicators['bb_middle'] = middle
        indicators['bb_lower'] = lower
        indicators['bb_width'] = (upper - lower) / middle
        indicators['bb_position'] = (df['close'] - lower) / (upper - lower)
        
        # Keltner Channels
        kc_period = 20
        kc_mult = 2
        kc_upper, kc_middle, kc_lower = keltner_channels(df['high'], df['low'], df['close'], kc_period, kc_mult)
        indicators['kc_upper'] = kc_upper
        indicators['kc_middle'] = kc_middle
        indicators['kc_lower'] = kc_lower
        
    except Exception as e:
        logger.error(f"Error computing volatility indicators: {e}")
    
    return indicators


def compute_volume_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """Compute volume-based indicators."""
    indicators = {}
    
    try:
        if 'volume' in df.columns and not df['volume'].isna().all():
            # Volume Moving Average
            indicators['volume_sma'] = sma(df['volume'], 20)
            
            # On-Balance Volume
            indicators['obv'] = on_balance_volume(df['close'], df['volume'])
            
            # Volume Rate of Change
            indicators['volume_roc'] = roc(df['volume'], 10)
            
            # Accumulation/Distribution Line
            indicators['ad_line'] = accumulation_distribution(df['high'], df['low'], df['close'], df['volume'])
            
        else:
            logger.warning("Volume data not available, skipping volume indicators")
            
    except Exception as e:
        logger.error(f"Error computing volume indicators: {e}")
    
    return indicators


def compute_support_resistance_indicators(df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, pd.Series]:
    """Compute support/resistance indicators."""
    indicators = {}
    
    try:
        # Donchian Channels
        donchian_period = config.get('entry', {}).get('donchian_period', 20)
        donchian_high, donchian_low, donchian_middle = donchian_channels(df['high'], df['low'], donchian_period)
        indicators['donchian_high'] = donchian_high
        indicators['donchian_low'] = donchian_low
        indicators['donchian_middle'] = donchian_middle
        
        # Pivot Points
        pivot, r1, r2, r3, s1, s2, s3 = pivot_points(df['high'], df['low'], df['close'])
        indicators['pivot'] = pivot
        indicators['r1'] = r1
        indicators['r2'] = r2
        indicators['r3'] = r3
        indicators['s1'] = s1
        indicators['s2'] = s2
        indicators['s3'] = s3
        
    except Exception as e:
        logger.error(f"Error computing support/resistance indicators: {e}")
    
    return indicators


# Individual indicator functions

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period).mean()


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """MACD (Moving Average Convergence Divergence)."""
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def roc(series: pd.Series, period: int) -> pd.Series:
    """Rate of Change."""
    return series.pct_change(period)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def stoch(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
    """Stochastic Oscillator."""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(window=d_period).mean()
    return k_percent, d_percent


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R."""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * ((highest_high - close) / (highest_high - lowest_low))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    high_low = high - low
    high_close = np.abs(high - close.shift())
    low_close = np.abs(low - close.shift())
    
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    return true_range.rolling(window=period).mean()


def bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Bollinger Bands."""
    middle = sma(series, period)
    std = series.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower


def keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20, multiplier: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Keltner Channels."""
    middle = ema(close, period)
    atr_line = atr(high, low, close, period)
    upper = middle + (atr_line * multiplier)
    lower = middle - (atr_line * multiplier)
    return upper, middle, lower


def donchian_channels(high: pd.Series, low: pd.Series, period: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Donchian Channels."""
    donchian_high = high.rolling(window=period).max()
    donchian_low = low.rolling(window=period).min()
    donchian_middle = (donchian_high + donchian_low) / 2
    return donchian_high, donchian_low, donchian_middle


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    obv = pd.Series(index=close.index, dtype=float)
    obv.iloc[0] = volume.iloc[0]
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    
    return obv


def accumulation_distribution(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Accumulation/Distribution Line."""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)  # Handle division by zero
    return (clv * volume).cumsum()


def pivot_points(high: pd.Series, low: pd.Series, close: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Pivot Points (Standard)."""
    pivot = (high + low + close) / 3
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    r3 = high + 2 * (pivot - low)
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    s3 = low - 2 * (high - pivot)
    return pivot, r1, r2, r3, s1, s2, s3


def get_indicator_value(indicators: Dict[str, pd.Series], indicator_name: str, index: int = -1) -> Optional[float]:
    """
    Get the latest value of an indicator.
    
    Args:
        indicators: Dictionary of indicators
        indicator_name: Name of the indicator
        index: Index to get value from (-1 for latest)
        
    Returns:
        Indicator value or None if not available
    """
    if indicator_name not in indicators:
        return None
    
    series = indicators[indicator_name]
    if series.empty or len(series) <= abs(index):
        return None
    
    try:
        return float(series.iloc[index])
    except (ValueError, TypeError):
        return None


def is_indicator_above(indicators: Dict[str, pd.Series], indicator1: str, indicator2: str, index: int = -1) -> bool:
    """Check if indicator1 is above indicator2."""
    val1 = get_indicator_value(indicators, indicator1, index)
    val2 = get_indicator_value(indicators, indicator2, index)
    
    if val1 is None or val2 is None:
        return False
    
    return val1 > val2


def is_indicator_below(indicators: Dict[str, pd.Series], indicator1: str, indicator2: str, index: int = -1) -> bool:
    """Check if indicator1 is below indicator2."""
    val1 = get_indicator_value(indicators, indicator1, index)
    val2 = get_indicator_value(indicators, indicator2, index)
    
    if val1 is None or val2 is None:
        return False
    
    return val1 < val2


def get_indicator_crossover(indicators: Dict[str, pd.Series], indicator1: str, indicator2: str, lookback: int = 2) -> Optional[str]:
    """
    Check for crossover between two indicators.
    
    Args:
        indicators: Dictionary of indicators
        indicator1: First indicator
        indicator2: Second indicator
        lookback: Number of periods to look back
        
    Returns:
        'bullish' if indicator1 crossed above indicator2,
        'bearish' if indicator1 crossed below indicator2,
        None if no crossover
    """
    if len(indicators.get(indicator1, pd.Series())) < lookback or len(indicators.get(indicator2, pd.Series())) < lookback:
        return None
    
    current_above = is_indicator_above(indicators, indicator1, indicator2, -1)
    previous_above = is_indicator_above(indicators, indicator1, indicator2, -2)
    
    if current_above and not previous_above:
        return 'bullish'
    elif not current_above and previous_above:
        return 'bearish'
    
    return None