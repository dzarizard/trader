"""
Tests for technical indicators.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.indicators import (
    compute_indicators, sma, ema, macd, roc, rsi, atr, 
    bollinger_bands, donchian_channels, get_indicator_value
)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
    np.random.seed(42)
    
    # Generate realistic price data
    base_price = 100
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


@pytest.fixture
def config():
    """Sample configuration for testing."""
    return {
        'trend': {
            'sma_fast': 20,
            'sma_mid': 50,
            'sma_long': 200
        },
        'entry': {
            'donchian_period': 20,
            'roc_lookback': 10,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9
        },
        'quality': {
            'atr_period': 14
        }
    }


def test_sma(sample_data):
    """Test Simple Moving Average calculation."""
    sma_20 = sma(sample_data['close'], 20)
    
    # Check that SMA is calculated correctly
    assert len(sma_20) == len(sample_data)
    assert sma_20.iloc[19] == sample_data['close'].iloc[:20].mean()  # First valid SMA value
    assert not sma_20.iloc[:18].notna().any()  # First 19 values should be NaN
    
    # Check that SMA values are reasonable
    assert sma_20.iloc[19:].min() > 0  # All SMA values should be positive


def test_ema(sample_data):
    """Test Exponential Moving Average calculation."""
    ema_12 = ema(sample_data['close'], 12)
    
    # Check that EMA is calculated
    assert len(ema_12) == len(sample_data)
    assert ema_12.iloc[0] == sample_data['close'].iloc[0]  # First EMA equals first price
    
    # Check that EMA values are reasonable
    assert ema_12.min() > 0  # All EMA values should be positive


def test_macd(sample_data):
    """Test MACD calculation."""
    macd_line, signal_line, histogram = macd(sample_data['close'], 12, 26, 9)
    
    # Check that all components are calculated
    assert len(macd_line) == len(sample_data)
    assert len(signal_line) == len(sample_data)
    assert len(histogram) == len(sample_data)
    
    # Check that histogram equals MACD - Signal
    assert np.allclose(histogram, macd_line - signal_line, equal_nan=True)


def test_roc(sample_data):
    """Test Rate of Change calculation."""
    roc_10 = roc(sample_data['close'], 10)
    
    # Check that ROC is calculated
    assert len(roc_10) == len(sample_data)
    assert not roc_10.iloc[:9].notna().any()  # First 10 values should be NaN
    
    # Check that ROC values are reasonable
    assert roc_10.iloc[10:].min() > -1  # ROC should not be less than -100%


def test_rsi(sample_data):
    """Test RSI calculation."""
    rsi_14 = rsi(sample_data['close'], 14)
    
    # Check that RSI is calculated
    assert len(rsi_14) == len(sample_data)
    assert not rsi_14.iloc[:13].notna().any()  # First 14 values should be NaN
    
    # Check that RSI values are in valid range
    valid_rsi = rsi_14.iloc[14:].dropna()
    assert valid_rsi.min() >= 0
    assert valid_rsi.max() <= 100


def test_atr(sample_data):
    """Test Average True Range calculation."""
    atr_14 = atr(sample_data['high'], sample_data['low'], sample_data['close'], 14)
    
    # Check that ATR is calculated
    assert len(atr_14) == len(sample_data)
    assert not atr_14.iloc[:13].notna().any()  # First 14 values should be NaN
    
    # Check that ATR values are positive
    assert atr_14.iloc[14:].min() > 0


def test_bollinger_bands(sample_data):
    """Test Bollinger Bands calculation."""
    upper, middle, lower = bollinger_bands(sample_data['close'], 20, 2)
    
    # Check that all bands are calculated
    assert len(upper) == len(sample_data)
    assert len(middle) == len(sample_data)
    assert len(lower) == len(sample_data)
    
    # Check that upper > middle > lower
    valid_indices = middle.notna()
    assert (upper[valid_indices] > middle[valid_indices]).all()
    assert (middle[valid_indices] > lower[valid_indices]).all()


def test_donchian_channels(sample_data):
    """Test Donchian Channels calculation."""
    high, low, middle = donchian_channels(sample_data['high'], sample_data['low'], 20)
    
    # Check that all channels are calculated
    assert len(high) == len(sample_data)
    assert len(low) == len(sample_data)
    assert len(middle) == len(sample_data)
    
    # Check that high >= middle >= low
    valid_indices = middle.notna()
    assert (high[valid_indices] >= middle[valid_indices]).all()
    assert (middle[valid_indices] >= low[valid_indices]).all()


def test_compute_indicators(sample_data, config):
    """Test complete indicator computation."""
    indicators = compute_indicators(sample_data, config)
    
    # Check that indicators are computed
    assert isinstance(indicators, dict)
    assert len(indicators) > 0
    
    # Check specific indicators
    expected_indicators = ['sma_20', 'sma_50', 'sma_200', 'macd', 'roc', 'atr']
    for indicator in expected_indicators:
        assert indicator in indicators
        assert isinstance(indicators[indicator], pd.Series)
        assert len(indicators[indicator]) == len(sample_data)


def test_get_indicator_value(sample_data, config):
    """Test getting indicator values."""
    indicators = compute_indicators(sample_data, config)
    
    # Test getting latest value
    sma_20_value = get_indicator_value(indicators, 'sma_20', -1)
    assert sma_20_value is not None
    assert isinstance(sma_20_value, (int, float))
    
    # Test getting value at specific index
    sma_20_value_0 = get_indicator_value(indicators, 'sma_20', 0)
    assert sma_20_value_0 is None  # Should be None for first values
    
    # Test getting value for non-existent indicator
    non_existent = get_indicator_value(indicators, 'non_existent', -1)
    assert non_existent is None


def test_empty_dataframe():
    """Test indicators with empty DataFrame."""
    empty_df = pd.DataFrame()
    config = {'trend': {'sma_fast': 20}}
    
    indicators = compute_indicators(empty_df, config)
    assert indicators == {}


def test_insufficient_data():
    """Test indicators with insufficient data."""
    # Create DataFrame with only 5 rows
    short_df = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100, 101, 102, 103, 104],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })
    
    config = {'trend': {'sma_fast': 20}}  # SMA period longer than data
    
    indicators = compute_indicators(short_df, config)
    
    # SMA should be all NaN
    assert indicators['sma_20'].isna().all()


def test_indicator_consistency(sample_data, config):
    """Test that indicators are consistent across multiple calls."""
    indicators1 = compute_indicators(sample_data, config)
    indicators2 = compute_indicators(sample_data, config)
    
    # Check that results are identical
    for indicator_name in indicators1:
        assert indicator_name in indicators2
        pd.testing.assert_series_equal(indicators1[indicator_name], indicators2[indicator_name])


def test_macd_crossover_detection(sample_data, config):
    """Test MACD crossover detection."""
    from app.indicators import get_indicator_crossover
    
    indicators = compute_indicators(sample_data, config)
    
    # Test crossover detection
    crossover = get_indicator_crossover(indicators, 'macd', 'macd_signal', 2)
    
    # Should return None, 'bullish', or 'bearish'
    assert crossover in [None, 'bullish', 'bearish']


def test_indicator_above_below(sample_data, config):
    """Test indicator comparison functions."""
    from app.indicators import is_indicator_above, is_indicator_below
    
    indicators = compute_indicators(sample_data, config)
    
    # Test above comparison
    above = is_indicator_above(indicators, 'sma_20', 'sma_50', -1)
    assert isinstance(above, bool)
    
    # Test below comparison
    below = is_indicator_below(indicators, 'sma_20', 'sma_50', -1)
    assert isinstance(below, bool)
    
    # Above and below should be opposite (when both are valid)
    if above is not None and below is not None:
        assert above != below