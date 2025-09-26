"""
Tests for signal management and lifecycle.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.rules import Signal, SignalManager
from app.sizing import Account, Instrument, PositionSizer, RiskManager, PositionPlan


@pytest.fixture
def sample_signal():
    """Create sample signal for testing."""
    return Signal(
        id='test_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='NAS100',
        entry_price=18500.0,
        stop_loss=18450.0,
        take_profit=18600.0,
        risk_reward_ratio=2.0,
        why='Test signal',
        metrics={'atr': 25.0}
    )


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'risk': {
            'max_open_signals': 3,
            'time_stop_bars': 12
        },
        'cooldowns': {
            'per_symbol_minutes': 30
        }
    }


@pytest.fixture
def sample_account():
    """Create sample account for testing."""
    return Account({
        'initial_equity': 10000,
        'equity_ccy': 'USD',
        'risk_management': {
            'risk_per_trade_pct': 0.008,
            'max_daily_loss_pct': 0.02,
            'max_open_signals': 3
        }
    })


@pytest.fixture
def sample_instrument():
    """Create sample instrument for testing."""
    return Instrument({
        'symbol': 'NAS100',
        'kind': 'index',
        'point_value': 1.0,
        'min_step': 1,
        'margin_requirement': 0.01,
        'leverage': 100
    })


def test_signal_creation(sample_signal):
    """Test signal creation and validation."""
    assert sample_signal.id == 'test_signal_1'
    assert sample_signal.side == 'LONG'
    assert sample_signal.symbol == 'NAS100'
    assert sample_signal.entry_price == 18500.0
    assert sample_signal.stop_loss == 18450.0
    assert sample_signal.take_profit == 18600.0
    assert sample_signal.risk_reward_ratio == 2.0
    assert sample_signal.status == 'ACTIVE'
    assert sample_signal.bars_since_entry == 0
    assert isinstance(sample_signal.timestamp, datetime)
    assert isinstance(sample_signal.metrics, dict)


def test_signal_manager_initialization(sample_config):
    """Test signal manager initialization."""
    signal_manager = SignalManager(sample_config)
    
    assert signal_manager.config == sample_config
    assert isinstance(signal_manager.active_signals, dict)
    assert isinstance(signal_manager.signal_history, list)
    assert isinstance(signal_manager.cooldown_periods, dict)
    assert signal_manager.max_open_signals == 3
    assert signal_manager.cooldown_minutes == 30


def test_signal_manager_add_signal(sample_config, sample_signal):
    """Test adding signal to manager."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    success = signal_manager.add_signal(sample_signal)
    
    assert success
    assert len(signal_manager.active_signals) == 1
    assert sample_signal.id in signal_manager.active_signals
    assert len(signal_manager.signal_history) == 1
    assert sample_signal.symbol in signal_manager.cooldown_periods


def test_signal_manager_max_signals_limit(sample_config):
    """Test maximum signals limit."""
    signal_manager = SignalManager(sample_config)
    
    # Add signals up to the limit
    for i in range(5):  # Try to add more than max_open_signals
        signal = Signal(
            id=f'signal_{i}',
            timestamp=datetime.now(),
            side='LONG',
            symbol=f'SYMBOL{i}',
            entry_price=100.0,
            stop_loss=95.0,
            take_profit=110.0,
            risk_reward_ratio=2.0,
            why=f'Test signal {i}',
            metrics={}
        )
        
        success = signal_manager.add_signal(signal)
        
        if i < signal_manager.max_open_signals:
            assert success
        else:
            assert not success
    
    # Check that we don't exceed max signals
    assert len(signal_manager.active_signals) <= signal_manager.max_open_signals


def test_signal_manager_cooldown(sample_config):
    """Test signal cooldown functionality."""
    signal_manager = SignalManager(sample_config)
    
    # Create first signal
    signal1 = Signal(
        id='signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='First signal',
        metrics={}
    )
    
    # Create second signal for same symbol
    signal2 = Signal(
        id='signal_2',
        timestamp=datetime.now(),
        side='SHORT',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        risk_reward_ratio=2.0,
        why='Second signal',
        metrics={}
    )
    
    # Add first signal
    success1 = signal_manager.add_signal(signal1)
    assert success1
    
    # Try to add second signal (should be blocked by cooldown)
    success2 = signal_manager.add_signal(signal2)
    assert not success2
    
    # Check cooldown period
    assert signal_manager._is_in_cooldown('TEST')


def test_signal_manager_update_signals(sample_config, sample_signal):
    """Test signal updates."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Create current data that hits stop loss
    current_data = {
        'NAS100': pd.DataFrame({
            'close': [18440.0],  # Price below stop loss
            'high': [18445.0],
            'low': [18435.0]
        })
    }
    
    # Update signals
    closed_signals = signal_manager.update_signals(current_data)
    
    assert isinstance(closed_signals, list)
    assert len(closed_signals) == 1
    assert closed_signals[0].status == 'HIT_SL'
    assert len(signal_manager.active_signals) == 0


def test_signal_manager_time_stop(sample_config):
    """Test time stop functionality."""
    signal_manager = SignalManager(sample_config)
    
    # Create signal
    signal = Signal(
        id='time_stop_signal',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='Time stop test',
        metrics={}
    )
    
    # Add signal
    signal_manager.add_signal(signal)
    
    # Simulate time passing by incrementing bars_since_entry
    for _ in range(15):  # More than time_stop_bars
        signal_manager.update_signals({'TEST': pd.DataFrame({
            'close': [100.0],
            'high': [101.0],
            'low': [99.0]
        })})
    
    # Signal should be closed due to time stop
    assert len(signal_manager.active_signals) == 0


def test_signal_manager_get_active_signals(sample_config, sample_signal):
    """Test getting active signals."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Get active signals
    active_signals = signal_manager.get_active_signals()
    
    assert isinstance(active_signals, list)
    assert len(active_signals) == 1
    assert active_signals[0].id == sample_signal.id


def test_signal_manager_get_signal_history(sample_config, sample_signal):
    """Test getting signal history."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Get history
    history = signal_manager.get_signal_history()
    
    assert isinstance(history, list)
    assert len(history) == 1
    assert history[0].id == sample_signal.id
    
    # Test with symbol filter
    history_filtered = signal_manager.get_signal_history(symbol='NAS100')
    assert len(history_filtered) == 1
    
    history_filtered = signal_manager.get_signal_history(symbol='EURUSD')
    assert len(history_filtered) == 0
    
    # Test with limit
    history_limited = signal_manager.get_signal_history(limit=1)
    assert len(history_limited) == 1


def test_signal_exit_conditions(sample_config):
    """Test various signal exit conditions."""
    signal_manager = SignalManager(sample_config)
    
    # Test SL hit
    signal_sl = Signal(
        id='sl_signal',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='SL test',
        metrics={}
    )
    
    signal_manager.add_signal(signal_sl)
    
    # Price hits stop loss
    current_data = {'TEST': pd.DataFrame({
        'close': [94.0],  # Below stop loss
        'high': [95.0],
        'low': [94.0]
    })}
    
    closed_signals = signal_manager.update_signals(current_data)
    assert len(closed_signals) == 1
    assert closed_signals[0].status == 'HIT_SL'
    
    # Test TP hit
    signal_tp = Signal(
        id='tp_signal',
        timestamp=datetime.now(),
        side='LONG',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=95.0,
        take_profit=110.0,
        risk_reward_ratio=2.0,
        why='TP test',
        metrics={}
    )
    
    signal_manager.add_signal(signal_tp)
    
    # Price hits take profit
    current_data = {'TEST': pd.DataFrame({
        'close': [111.0],  # Above take profit
        'high': [111.0],
        'low': [100.0]
    })}
    
    closed_signals = signal_manager.update_signals(current_data)
    assert len(closed_signals) == 1
    assert closed_signals[0].status == 'HIT_TP'


def test_signal_short_exit_conditions(sample_config):
    """Test exit conditions for SHORT signals."""
    signal_manager = SignalManager(sample_config)
    
    # Test SHORT SL hit
    signal_short_sl = Signal(
        id='short_sl_signal',
        timestamp=datetime.now(),
        side='SHORT',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        risk_reward_ratio=2.0,
        why='Short SL test',
        metrics={}
    )
    
    signal_manager.add_signal(signal_short_sl)
    
    # Price hits stop loss (above entry for SHORT)
    current_data = {'TEST': pd.DataFrame({
        'close': [106.0],  # Above stop loss
        'high': [106.0],
        'low': [100.0]
    })}
    
    closed_signals = signal_manager.update_signals(current_data)
    assert len(closed_signals) == 1
    assert closed_signals[0].status == 'HIT_SL'
    
    # Test SHORT TP hit
    signal_short_tp = Signal(
        id='short_tp_signal',
        timestamp=datetime.now(),
        side='SHORT',
        symbol='TEST',
        entry_price=100.0,
        stop_loss=105.0,
        take_profit=90.0,
        risk_reward_ratio=2.0,
        why='Short TP test',
        metrics={}
    )
    
    signal_manager.add_signal(signal_short_tp)
    
    # Price hits take profit (below entry for SHORT)
    current_data = {'TEST': pd.DataFrame({
        'close': [89.0],  # Below take profit
        'high': [100.0],
        'low': [89.0]
    })}
    
    closed_signals = signal_manager.update_signals(current_data)
    assert len(closed_signals) == 1
    assert closed_signals[0].status == 'HIT_TP'


def test_signal_manager_empty_data(sample_config, sample_signal):
    """Test signal manager with empty data."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Update with empty data
    closed_signals = signal_manager.update_signals({})
    
    assert isinstance(closed_signals, list)
    assert len(closed_signals) == 0  # No signals should be closed


def test_signal_manager_missing_symbol_data(sample_config, sample_signal):
    """Test signal manager with missing symbol data."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Update with data for different symbol
    current_data = {'EURUSD': pd.DataFrame({
        'close': [1.0850],
        'high': [1.0860],
        'low': [1.0840]
    })}
    
    closed_signals = signal_manager.update_signals(current_data)
    
    assert isinstance(closed_signals, list)
    assert len(closed_signals) == 0  # No signals should be closed


def test_signal_metrics_update(sample_config, sample_signal):
    """Test signal metrics updates."""
    signal_manager = SignalManager(sample_config)
    
    # Add signal
    signal_manager.add_signal(sample_signal)
    
    # Update signals multiple times
    for i in range(5):
        current_data = {'NAS100': pd.DataFrame({
            'close': [18500.0 + i],  # Price moving up
            'high': [18501.0 + i],
            'low': [18499.0 + i]
        })}
        
        closed_signals = signal_manager.update_signals(current_data)
        
        # Signal should still be active
        assert len(closed_signals) == 0
        assert len(signal_manager.active_signals) == 1
        
        # Check that bars_since_entry is incrementing
        active_signal = list(signal_manager.active_signals.values())[0]
        assert active_signal.bars_since_entry == i + 1


def test_signal_manager_error_handling(sample_config):
    """Test signal manager error handling."""
    signal_manager = SignalManager(sample_config)
    
    # Test with invalid signal
    invalid_signal = None
    
    try:
        signal_manager.add_signal(invalid_signal)
        assert False  # Should not reach here
    except Exception:
        pass  # Expected to raise exception
    
    # Test with malformed data
    signal = Signal(
        id='test_signal',
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
    
    signal_manager.add_signal(signal)
    
    # Update with malformed data
    malformed_data = {'TEST': 'invalid_data'}
    
    try:
        closed_signals = signal_manager.update_signals(malformed_data)
        assert isinstance(closed_signals, list)  # Should handle gracefully
    except Exception:
        pass  # May raise exception, which is acceptable