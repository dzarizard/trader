"""
Tests for position sizing and risk management.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.sizing import Account, Instrument, PositionSizer, RiskManager, PositionPlan
from app.rules import Signal


@pytest.fixture
def sample_account():
    """Create sample account for testing."""
    return Account({
        'initial_equity': 10000,
        'equity_ccy': 'USD',
        'risk_management': {
            'risk_per_trade_pct': 0.008,
            'max_daily_loss_pct': 0.02,
            'max_open_signals': 5
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


@pytest.fixture
def sample_fx_instrument():
    """Create sample FX instrument for testing."""
    return Instrument({
        'symbol': 'EURUSD',
        'kind': 'fx',
        'pip_value': 10.0,
        'min_step': 0.0001,
        'lot_size': 100000,
        'margin_requirement': 0.01,
        'leverage': 100
    })


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


def test_account_initialization(sample_account):
    """Test account initialization."""
    assert sample_account.equity == 10000
    assert sample_account.currency == 'USD'
    assert sample_account.risk_per_trade_pct == 0.008
    assert sample_account.max_daily_loss_pct == 0.02
    assert sample_account.max_open_signals == 5


def test_account_can_trade(sample_account):
    """Test account trading permission."""
    can_trade, reason = sample_account.can_trade()
    
    assert isinstance(can_trade, bool)
    assert isinstance(reason, str)
    assert can_trade  # Should be able to trade initially


def test_account_available_risk(sample_account):
    """Test available risk calculation."""
    available_risk = sample_account.get_available_risk()
    
    assert isinstance(available_risk, float)
    assert available_risk > 0
    assert available_risk <= sample_account.equity * sample_account.risk_per_trade_pct


def test_account_daily_loss_limit(sample_account):
    """Test daily loss limit functionality."""
    # Simulate daily loss
    sample_account.daily_pnl = -sample_account.equity * sample_account.max_daily_loss_pct - 100
    
    can_trade, reason = sample_account.can_trade()
    
    assert not can_trade
    assert 'Daily loss limit' in reason


def test_instrument_initialization(sample_instrument):
    """Test instrument initialization."""
    assert sample_instrument.symbol == 'NAS100'
    assert sample_instrument.kind == 'index'
    assert sample_instrument.point_value == 1.0
    assert sample_instrument.min_step == 1
    assert sample_instrument.margin_requirement == 0.01
    assert sample_instrument.leverage == 100


def test_instrument_point_value(sample_instrument, sample_fx_instrument):
    """Test point value calculation."""
    # Test index instrument
    point_value = sample_instrument.get_point_value('LONG')
    assert point_value == 1.0
    
    # Test FX instrument
    pip_value = sample_fx_instrument.get_pip_value('LONG')
    assert pip_value == 10.0


def test_instrument_pip_distance(sample_fx_instrument):
    """Test pip distance calculation."""
    distance = sample_fx_instrument.calculate_pip_distance(1.0850, 1.0840)
    assert distance == 100  # 10 pips
    
    distance = sample_fx_instrument.calculate_pip_distance(1.0840, 1.0850)
    assert distance == 100  # 10 pips (absolute value)


def test_instrument_position_value(sample_instrument, sample_fx_instrument):
    """Test position value calculation."""
    # Test index instrument
    index_value = sample_instrument.calculate_position_value(1.0, 18500.0)
    assert index_value == 18500.0
    
    # Test FX instrument
    fx_value = sample_fx_instrument.calculate_position_value(1.0, 1.0850)
    assert fx_value == 108500.0  # 1 lot * 100000 * price


def test_position_sizer_calculation(sample_account, sample_instrument, sample_signal):
    """Test position size calculation."""
    sizer = PositionSizer(sample_account)
    
    position_plan = sizer.calculate_position_size(sample_signal, sample_instrument)
    
    assert isinstance(position_plan, PositionPlan)
    assert position_plan.size_units > 0
    assert position_plan.risk_amount > 0
    assert position_plan.risk_pct > 0
    assert position_plan.value_per_point > 0
    assert position_plan.max_loss > 0
    assert position_plan.potential_profit > 0
    assert position_plan.position_value > 0
    assert position_plan.margin_required > 0
    assert position_plan.leverage > 0


def test_position_sizer_fx(sample_account, sample_fx_instrument):
    """Test position size calculation for FX."""
    sizer = PositionSizer(sample_account)
    
    # Create FX signal
    fx_signal = Signal(
        id='fx_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='EURUSD',
        entry_price=1.0850,
        stop_loss=1.0820,
        take_profit=1.0910,
        risk_reward_ratio=2.0,
        why='FX test signal',
        metrics={'atr': 0.0015}
    )
    
    position_plan = sizer.calculate_position_size(fx_signal, sample_fx_instrument)
    
    assert isinstance(position_plan, PositionPlan)
    assert position_plan.size_units > 0
    assert position_plan.risk_amount > 0
    assert position_plan.risk_pct > 0


def test_position_sizer_short_signal(sample_account, sample_instrument):
    """Test position size calculation for SHORT signal."""
    sizer = PositionSizer(sample_account)
    
    # Create SHORT signal
    short_signal = Signal(
        id='short_signal_1',
        timestamp=datetime.now(),
        side='SHORT',
        symbol='NAS100',
        entry_price=18500.0,
        stop_loss=18550.0,
        take_profit=18400.0,
        risk_reward_ratio=2.0,
        why='Short test signal',
        metrics={'atr': 25.0}
    )
    
    position_plan = sizer.calculate_position_size(short_signal, sample_instrument)
    
    assert isinstance(position_plan, PositionPlan)
    assert position_plan.size_units > 0
    assert position_plan.risk_amount > 0
    assert position_plan.risk_pct > 0


def test_position_sizer_invalid_risk(sample_account, sample_instrument):
    """Test position size calculation with invalid risk."""
    sizer = PositionSizer(sample_account)
    
    # Create signal with invalid risk (stop loss above entry for LONG)
    invalid_signal = Signal(
        id='invalid_signal_1',
        timestamp=datetime.now(),
        side='LONG',
        symbol='NAS100',
        entry_price=18500.0,
        stop_loss=18600.0,  # Stop loss above entry (invalid)
        take_profit=18700.0,
        risk_reward_ratio=2.0,
        why='Invalid test signal',
        metrics={'atr': 25.0}
    )
    
    position_plan = sizer.calculate_position_size(invalid_signal, sample_instrument)
    
    # Should return empty plan
    assert position_plan.size_units == 0
    assert position_plan.risk_amount == 0


def test_risk_manager_initialization(sample_account):
    """Test risk manager initialization."""
    risk_manager = RiskManager(sample_account)
    
    assert risk_manager.account == sample_account
    assert isinstance(risk_manager.active_positions, dict)
    assert isinstance(risk_manager.daily_stats, dict)


def test_risk_manager_validate_signal(sample_account, sample_instrument, sample_signal):
    """Test signal validation."""
    risk_manager = RiskManager(sample_account)
    
    is_valid, reason = risk_manager.validate_signal(sample_signal, sample_instrument)
    
    assert isinstance(is_valid, bool)
    assert isinstance(reason, str)
    assert is_valid  # Should be valid initially


def test_risk_manager_max_signals(sample_account, sample_instrument):
    """Test maximum signals limit."""
    risk_manager = RiskManager(sample_account)
    
    # Add multiple signals to test max limit
    for i in range(10):  # Try to add more than max_open_signals
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
        
        is_valid, reason = risk_manager.validate_signal(signal, sample_instrument)
        
        if i < sample_account.max_open_signals:
            assert is_valid
        else:
            assert not is_valid
            assert 'Maximum open signals' in reason


def test_risk_manager_duplicate_symbol(sample_account, sample_instrument):
    """Test duplicate symbol validation."""
    risk_manager = RiskManager(sample_account)
    
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
    
    # Validate first signal
    is_valid1, reason1 = risk_manager.validate_signal(signal1, sample_instrument)
    assert is_valid1
    
    # Add first signal
    risk_manager.add_position(signal1, PositionPlan(
        size_units=1.0,
        risk_amount=100.0,
        risk_pct=1.0,
        value_per_point=1.0,
        max_loss=100.0,
        potential_profit=200.0,
        position_value=10000.0,
        margin_required=100.0,
        leverage=100.0
    ), sample_instrument)
    
    # Validate second signal (should be rejected)
    is_valid2, reason2 = risk_manager.validate_signal(signal2, sample_instrument)
    assert not is_valid2
    assert 'Already have position' in reason2


def test_risk_manager_add_position(sample_account, sample_instrument, sample_signal):
    """Test adding position."""
    risk_manager = RiskManager(sample_account)
    
    position_plan = PositionPlan(
        size_units=1.0,
        risk_amount=100.0,
        risk_pct=1.0,
        value_per_point=1.0,
        max_loss=100.0,
        potential_profit=200.0,
        position_value=10000.0,
        margin_required=100.0,
        leverage=100.0
    )
    
    risk_manager.add_position(sample_signal, position_plan, sample_instrument)
    
    assert len(risk_manager.active_positions) == 1
    assert sample_signal.id in risk_manager.active_positions
    assert risk_manager.daily_stats['trades'] == 1


def test_risk_manager_update_positions(sample_account, sample_instrument, sample_signal):
    """Test position updates."""
    risk_manager = RiskManager(sample_account)
    
    position_plan = PositionPlan(
        size_units=1.0,
        risk_amount=100.0,
        risk_pct=1.0,
        value_per_point=1.0,
        max_loss=100.0,
        potential_profit=200.0,
        position_value=10000.0,
        margin_required=100.0,
        leverage=100.0
    )
    
    # Add position
    risk_manager.add_position(sample_signal, position_plan, sample_instrument)
    
    # Update with current prices
    current_prices = {'NAS100': 18600.0}  # Price hit take profit
    closed_positions = risk_manager.update_positions(current_prices)
    
    assert isinstance(closed_positions, list)
    # Position should be closed due to TP hit
    assert len(closed_positions) == 1
    assert closed_positions[0]['exit_reason'] == 'HIT_TP'


def test_risk_manager_portfolio_summary(sample_account):
    """Test portfolio summary."""
    risk_manager = RiskManager(sample_account)
    
    summary = risk_manager.get_portfolio_summary()
    
    assert isinstance(summary, dict)
    assert 'account_equity' in summary
    assert 'daily_pnl' in summary
    assert 'total_exposure' in summary
    assert 'total_risk' in summary
    assert 'active_positions' in summary
    assert 'max_positions' in summary
    assert 'win_rate' in summary


def test_risk_manager_position_details(sample_account, sample_instrument, sample_signal):
    """Test position details."""
    risk_manager = RiskManager(sample_account)
    
    position_plan = PositionPlan(
        size_units=1.0,
        risk_amount=100.0,
        risk_pct=1.0,
        value_per_point=1.0,
        max_loss=100.0,
        potential_profit=200.0,
        position_value=10000.0,
        margin_required=100.0,
        leverage=100.0
    )
    
    # Add position
    risk_manager.add_position(sample_signal, position_plan, sample_instrument)
    
    # Get position details
    details = risk_manager.get_position_details(sample_signal.id)
    
    assert isinstance(details, dict)
    assert 'signal' in details
    assert 'position_plan' in details
    assert 'instrument' in details
    assert 'entry_time' in details
    assert 'status' in details
    assert details['status'] == 'OPEN'


def test_position_plan_validation():
    """Test position plan validation."""
    position_plan = PositionPlan(
        size_units=1.0,
        risk_amount=100.0,
        risk_pct=1.0,
        value_per_point=1.0,
        max_loss=100.0,
        potential_profit=200.0,
        position_value=10000.0,
        margin_required=100.0,
        leverage=100.0
    )
    
    assert position_plan.size_units == 1.0
    assert position_plan.risk_amount == 100.0
    assert position_plan.risk_pct == 1.0
    assert position_plan.value_per_point == 1.0
    assert position_plan.max_loss == 100.0
    assert position_plan.potential_profit == 200.0
    assert position_plan.position_value == 10000.0
    assert position_plan.margin_required == 100.0
    assert position_plan.leverage == 100.0


def test_risk_calculation_consistency(sample_account, sample_instrument, sample_signal):
    """Test that risk calculations are consistent."""
    sizer = PositionSizer(sample_account)
    
    position_plan = sizer.calculate_position_size(sample_signal, sample_instrument)
    
    # Risk amount should equal max loss
    assert abs(position_plan.risk_amount - position_plan.max_loss) < 0.01
    
    # Risk percentage should be calculated correctly
    expected_risk_pct = (position_plan.risk_amount / sample_account.equity) * 100
    assert abs(position_plan.risk_pct - expected_risk_pct) < 0.01
    
    # Position value should be calculated correctly
    expected_position_value = position_plan.size_units * sample_signal.entry_price * position_plan.value_per_point
    assert abs(position_plan.position_value - expected_position_value) < 0.01