"""
Tests for trading rules and signal generation.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add app directory to path
sys.path.append(os.path.dirname(__file__), '..', 'app'))

from app.rules import (
    TrendFilter, EntryTrigger, QualityFilter, SignalGenerator, SignalManager, Signal
)
from app.indicators import compute_indicators


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
            'roc_min_long': 0.003,
            'roc_max_short': -0.003,
            'macd_fast': 12,
            'macd_slow': 26,
            'macd_signal': 9
        },
        'quality': {
            'vol_mult': 1.2,
            'atr_min_pct': 0.003,
            'atr_max_pct': 0.03,
            'atr_period': 14
        },
        'risk': {
            'stop_atr_mult': 1.5,
            'rr_ratio': 2.0,
            'time_stop_bars': 12
        }
    }


@pytest.fixture
def indicators(sample_data, config):
    """Compute indicators for sample data."""
    return compute_indicators(sample_data, config)


def test_trend_filter_long(sample_data, config, indicators):
    """Test trend filter for LONG signals."""
    trend_filter = TrendFilter(config)
    
    # Test LONG trend check
    is_valid, reason = trend_filter.check_trend(indicators, 'LONG')
    
    assert isinstance(is_valid, bool)
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_trend_filter_short(sample_data, config, indicators):
    """Test trend filter for SHORT signals."""
    trend_filter = TrendFilter(config)
    
    # Test SHORT trend check
    is_valid, reason = trend_filter.check_trend(indicators, 'SHORT')
    
    assert isinstance(is_valid, bool)
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_trend_filter_invalid_side(sample_data, config, indicators):
    """Test trend filter with invalid side."""
    trend_filter = TrendFilter(config)
    
    # Test invalid side
    is_valid, reason = trend_filter.check_trend(indicators, 'INVALID')
    
    assert not is_valid
    assert 'Invalid side' in reason


def test_entry_trigger_long(sample_data, config, indicators):
    """Test entry trigger for LONG signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test LONG entry triggers
    is_triggered, reason = entry_trigger.check_entry_triggers(sample_data, indicators, 'LONG')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_entry_trigger_short(sample_data, config, indicators):
    """Test entry trigger for SHORT signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test SHORT entry triggers
    is_triggered, reason = entry_trigger.check_entry_triggers(sample_data, indicators, 'SHORT')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_donchian_breakout_long(sample_data, config, indicators):
    """Test Donchian breakout for LONG signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test Donchian breakout
    is_triggered, reason = entry_trigger._check_donchian_breakout(sample_data, indicators, 'LONG')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_donchian_breakout_short(sample_data, config, indicators):
    """Test Donchian breakout for SHORT signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test Donchian breakout
    is_triggered, reason = entry_trigger._check_donchian_breakout(sample_data, indicators, 'SHORT')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_macd_crossover_long(sample_data, config, indicators):
    """Test MACD crossover for LONG signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test MACD crossover
    is_triggered, reason = entry_trigger._check_macd_crossover(indicators, 'LONG')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_macd_crossover_short(sample_data, config, indicators):
    """Test MACD crossover for SHORT signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test MACD crossover
    is_triggered, reason = entry_trigger._check_macd_crossover(indicators, 'SHORT')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_roc_momentum_long(sample_data, config, indicators):
    """Test ROC momentum for LONG signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test ROC momentum
    is_triggered, reason = entry_trigger._check_roc_momentum(indicators, 'LONG')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_roc_momentum_short(sample_data, config, indicators):
    """Test ROC momentum for SHORT signals."""
    entry_trigger = EntryTrigger(config)
    
    # Test ROC momentum
    is_triggered, reason = entry_trigger._check_roc_momentum(indicators, 'SHORT')
    
    assert isinstance(is_triggered, bool)
    assert isinstance(reason, str)


def test_quality_filter(sample_data, config, indicators):
    """Test quality filter."""
    quality_filter = QualityFilter(config)
    
    # Test quality check
    is_quality, reason = quality_filter.check_quality(sample_data, indicators)
    
    assert isinstance(is_quality, bool)
    assert isinstance(reason, str)
    assert len(reason) > 0


def test_volume_check(sample_data, config, indicators):
    """Test volume quality check."""
    quality_filter = QualityFilter(config)
    
    # Test volume check
    volume_reason = quality_filter._check_volume(sample_data, indicators)
    
    # Should return string or None
    assert volume_reason is None or isinstance(volume_reason, str)


def test_volatility_check(sample_data, config, indicators):
    """Test volatility quality check."""
    quality_filter = QualityFilter(config)
    
    # Test volatility check
    volatility_reason = quality_filter._check_volatility(sample_data, indicators)
    
    # Should return string or None
    assert volatility_reason is None or isinstance(volatility_reason, str)


def test_signal_generator(sample_data, config):
    """Test signal generator."""
    signal_generator = SignalGenerator(config)
    
    # Test signal generation
    signals = signal_generator.generate_signals(sample_data, sample_data, 'TEST')
    
    assert isinstance(signals, list)
    
    # Check signal structure if any signals generated
    for signal in signals:
        assert isinstance(signal, Signal)
        assert signal.side in ['LONG', 'SHORT']
        assert signal.symbol == 'TEST'
        assert signal.entry_price > 0
        assert signal.stop_loss > 0
        assert signal.take_profit > 0
        assert signal.risk_reward_ratio > 0
        assert len(signal.why) > 0
        assert isinstance(signal.metrics, dict)


def test_signal_manager(config):
    """Test signal manager."""
    signal_manager = SignalManager(config)
    
    # Create a test signal
    test_signal = Signal(
        id='test_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='Test signal',
        metrics={}
    )
    
    # Test adding signal
    success = signal_manager.add_signal(test_signal)
    assert isinstance(success, bool)
    
    # Test getting active signals
    active_signals = signal_manager.get_active_signals()
    assert isinstance(active_signals, list)
    
    # Test getting signal history
    history = signal_manager.get_signal_history()
    assert isinstance(history, list)


def test_signal_manager_cooldown(config):
    """Test signal manager cooldown functionality."""
    signal_manager = SignalManager(config)
    
    # Create a test signal
    test_signal = Signal(
        id='test_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='Test signal',
        metrics={}
    )
    
    # Add first signal
    success1 = signal_manager.add_signal(test_signal)
    
    # Try to add another signal for same symbol (should be blocked by cooldown)
    test_signal2 = Signal(
        id='test_signal_2',
        timestamp=datetime.now(),
        side='SHORT',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        risk_reward_ratio=2.0,
        why='Test signal 2',
        metrics={}
    )
    
    success2 = signal_manager.add_signal(test_signal2)
    
    # Second signal should be blocked by cooldown
    if success1:
        assert not success2


def test_signal_manager_max_signals(config):
    """Test signal manager maximum signals limit."""
    signal_manager = SignalManager(config)
    
    # Add multiple signals to test max limit
    for i in range(10):  # Try to add more than max_open_signals
        test_signal = Signal(
            id=f'test_signal_{i}',
            timestamp=datetime.now(),
            side='LONG',
            symbol=f'TEST{i}',
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            why=f'Test signal {i}',
            metrics={}
        )
        
        signal_manager.add_signal(test_signal)
    
    # Check that we don't exceed max signals
    active_signals = signal_manager.get_active_signals()
    max_signals = config.get('risk', {}).get('max_open_signals', 5)
    assert len(active_signals) <= max_signals


def test_signal_update_positions(config):
    """Test signal position updates."""
    signal_manager = SignalManager(config)
    
    # Create a test signal
    test_signal = Signal(
        id='test_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='Test signal',
        metrics={}
    )
    
    # Add signal
    signal_manager.add_signal(test_signal)
    
    # Create current data
    current_data = {
        'TEST': pd.DataFrame({
            'close': [98.0],  # Price below stop loss
            'high': [99.0],
            'low': [97.0]
        })
    }
    
    # Update positions
    closed_signals = signal_manager.update_signals(current_data)
    
    assert isinstance(closed_signals, list)


def test_signal_validation(sample_data, config):
    """Test signal validation logic."""
    signal_generator = SignalGenerator(config)
    
    # Test with empty data
    empty_signals = signal_generator.generate_signals(
        pd.DataFrame(), pd.DataFrame(), 'TEST'
    )
    assert empty_signals == []
    
    # Test with insufficient data
    short_data = sample_data.head(10)  # Not enough for indicators
    short_signals = signal_generator.generate_signals(short_data, short_data, 'TEST')
    assert isinstance(short_signals, list)


def test_signal_metrics_calculation(sample_data, config):
    """Test signal metrics calculation."""
    signal_generator = SignalGenerator(config)
    
    # Generate signals
    signals = signal_generator.generate_signals(sample_data, sample_data, 'TEST')
    
    for signal in signals:
        metrics = signal.metrics
        
        # Check that metrics are calculated
        assert isinstance(metrics, dict)
        
        # Check specific metrics
        if 'atr' in metrics:
            assert metrics['atr'] > 0
        
        if 'atr_pct' in metrics:
            assert 0 <= metrics['atr_pct'] <= 1
        
        if 'volume_ratio' in metrics:
            assert metrics['volume_ratio'] is None or metrics['volume_ratio'] > 0
        
        if 'trend_strength' in metrics:
            assert metrics['trend_strength'] in [-1.0, 0.0, 1.0, None]
        
        if 'momentum_score' in metrics:
            assert 0 <= metrics['momentum_score'] <= 1 or metrics['momentum_score'] is None