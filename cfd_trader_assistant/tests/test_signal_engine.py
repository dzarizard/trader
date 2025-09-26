"""
Tests for signal engine functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.signal_engine import SignalEngine, Signal, SignalState


class TestSignalEngine:
    """Test signal engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'trend': {
                'sma_long': 200,
                'sma_mid': 50,
                'sma_fast': 20
            },
            'entry': {
                'donchian_period': 20,
                'roc_lookback': 10,
                'roc_min_long': 0.003,
                'roc_max_short': -0.003
            },
            'quality': {
                'vol_mult': 1.2,
                'atr_min_pct': 0.003,
                'atr_max_pct': 0.03
            },
            'risk': {
                'stop_atr_mult': 1.5,
                'rr_ratio': 2.0,
                'time_stop_bars': 12
            },
            'cooldowns': {
                'per_symbol_minutes': 30
            },
            'fees': {
                'spread': 0.0001,
                'commission': 0.0001,
                'swap_rate': 0.0001
            }
        }
        self.signal_engine = SignalEngine(self.config)
    
    def create_sample_data(self, periods=300, interval='5m'):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq=interval)
        
        # Create realistic price data with trend
        base_price = 100.0
        trend = np.linspace(0, 10, periods)  # Upward trend
        noise = np.random.normal(0, 0.5, periods)
        prices = base_price + trend + noise
        
        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Add some volatility
            volatility = 0.01
            high = price * (1 + volatility)
            low = price * (1 - volatility)
            open_price = prices[i-1] if i > 0 else price
            close = price
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'timestamp': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def test_get_closed_bars(self):
        """Test getting only closed bars."""
        # Create data with current incomplete bar
        df = self.create_sample_data(100)
        
        # Simulate current time being very close to last bar
        closed_bars = self.signal_engine._get_closed_bars(df)
        
        # Should exclude the last bar if it's too recent
        assert len(closed_bars) <= len(df)
        assert len(closed_bars) >= len(df) - 1
    
    def test_shift_htf_indicators(self):
        """Test shifting HTF indicators to prevent look-ahead bias."""
        # Create sample indicators
        htf_indicators = {
            'sma_20': pd.Series([100, 101, 102, 103, 104]),
            'sma_50': pd.Series([98, 99, 100, 101, 102]),
            'close': pd.Series([105, 106, 107, 108, 109])
        }
        
        shifted = self.signal_engine._shift_htf_indicators(htf_indicators)
        
        # Check that all series are shifted by 1
        for name, series in shifted.items():
            assert pd.isna(series.iloc[0])  # First value should be NaN
            assert series.iloc[1] == htf_indicators[name].iloc[0]  # Second value should be first original
    
    def test_check_trend_filter_long(self):
        """Test trend filter for LONG signals."""
        # Create indicators with bullish trend
        htf_indicators = {
            'close': pd.Series([105.0]),
            'sma_200': pd.Series([100.0]),
            'sma_50': pd.Series([102.0]),
            'sma_20': pd.Series([104.0])
        }
        
        is_valid, reason = self.signal_engine._check_trend_filter(htf_indicators, 'LONG')
        
        assert is_valid
        assert 'Trend(HTF) OK' in reason
        assert 'Close(105.00) > SMA200(100.00)' in reason
        assert 'SMA20(104.00) > SMA50(102.00)' in reason
    
    def test_check_trend_filter_short(self):
        """Test trend filter for SHORT signals."""
        # Create indicators with bearish trend
        htf_indicators = {
            'close': pd.Series([95.0]),
            'sma_200': pd.Series([100.0]),
            'sma_50': pd.Series([98.0]),
            'sma_20': pd.Series([96.0])
        }
        
        is_valid, reason = self.signal_engine._check_trend_filter(htf_indicators, 'SHORT')
        
        assert is_valid
        assert 'Trend(HTF) OK' in reason
        assert 'Close(95.00) < SMA200(100.00)' in reason
        assert 'SMA20(96.00) < SMA50(98.00)' in reason
    
    def test_check_trend_filter_invalid_long(self):
        """Test trend filter failure for LONG signals."""
        # Create indicators with bearish trend
        htf_indicators = {
            'close': pd.Series([95.0]),
            'sma_200': pd.Series([100.0]),
            'sma_50': pd.Series([98.0]),
            'sma_20': pd.Series([96.0])
        }
        
        is_valid, reason = self.signal_engine._check_trend_filter(htf_indicators, 'LONG')
        
        assert not is_valid
        assert 'Trend(HTF) FAIL' in reason
    
    def test_check_donchian_breakout_long(self):
        """Test Donchian breakout for LONG signals."""
        # Create data with breakout
        ltf_data = pd.DataFrame({
            'high': [100, 101, 102, 103, 105],  # Breakout on last bar
            'low': [99, 100, 101, 102, 103]
        })
        
        ltf_indicators = {
            'donchian_high': pd.Series([104.0]),  # Previous high
            'donchian_low': pd.Series([99.0])
        }
        
        is_valid, reason = self.signal_engine._check_donchian_breakout(ltf_data, ltf_indicators, 'LONG')
        
        assert is_valid
        assert 'Breakout(20)' in reason
        assert 'High(105.00) > Donchian(104.00)' in reason
    
    def test_check_donchian_breakout_short(self):
        """Test Donchian breakout for SHORT signals."""
        # Create data with breakdown
        ltf_data = pd.DataFrame({
            'high': [100, 101, 102, 103, 104],
            'low': [99, 100, 101, 102, 98]  # Breakdown on last bar
        })
        
        ltf_indicators = {
            'donchian_high': pd.Series([104.0],
            'donchian_low': pd.Series([99.5])  # Previous low
        }
        
        is_valid, reason = self.signal_engine._check_donchian_breakout(ltf_data, ltf_indicators, 'SHORT')
        
        assert is_valid
        assert 'Breakout(20)' in reason
        assert 'Low(98.00) < Donchian(99.50)' in reason
    
    def test_check_macd_crossover_long(self):
        """Test MACD crossover for LONG signals."""
        ltf_indicators = {
            'macd': pd.Series([0.1]),  # Above signal and zero
            'macd_signal': pd.Series([0.05])
        }
        
        is_valid, reason = self.signal_engine._check_macd_crossover(ltf_indicators, 'LONG')
        
        assert is_valid
        assert 'MACD Cross' in reason
        assert 'MACD(0.1000) > Signal(0.0500) > 0' in reason
    
    def test_check_macd_crossover_short(self):
        """Test MACD crossover for SHORT signals."""
        ltf_indicators = {
            'macd': pd.Series([-0.1]),  # Below signal and zero
            'macd_signal': pd.Series([-0.05])
        }
        
        is_valid, reason = self.signal_engine._check_macd_crossover(ltf_indicators, 'SHORT')
        
        assert is_valid
        assert 'MACD Cross' in reason
        assert 'MACD(-0.1000) < Signal(-0.0500) < 0' in reason
    
    def test_check_roc_momentum_long(self):
        """Test ROC momentum for LONG signals."""
        ltf_indicators = {
            'roc': pd.Series([0.005])  # Above minimum threshold
        }
        
        is_valid, reason = self.signal_engine._check_roc_momentum(ltf_indicators, 'LONG')
        
        assert is_valid
        assert 'ROC(10)' in reason
        assert '0.005 >= 0.003' in reason
    
    def test_check_roc_momentum_short(self):
        """Test ROC momentum for SHORT signals."""
        ltf_indicators = {
            'roc': pd.Series([-0.005])  # Below maximum threshold
        }
        
        is_valid, reason = self.signal_engine._check_roc_momentum(ltf_indicators, 'SHORT')
        
        assert is_valid
        assert 'ROC(10)' in reason
        assert '-0.005 <= -0.003' in reason
    
    def test_check_volume(self):
        """Test volume check."""
        ltf_data = pd.DataFrame({
            'volume': [1500]  # High volume
        })
        
        ltf_indicators = {
            'volume_sma': pd.Series([1000.0])  # Average volume
        }
        
        result = self.signal_engine._check_volume(ltf_data, ltf_indicators)
        
        assert result is not None
        assert 'Vol 1.5×' in result
    
    def test_check_volatility(self):
        """Test volatility check."""
        ltf_data = pd.DataFrame({
            'close': [100.0]
        })
        
        ltf_indicators = {
            'atr': pd.Series([0.5])  # 0.5% ATR
        }
        
        result = self.signal_engine._check_volatility(ltf_data, ltf_indicators)
        
        assert result is not None
        assert 'ATR 0.5%' in result
    
    def test_is_in_cooldown(self):
        """Test cooldown check."""
        symbol = 'EURUSD'
        
        # Initially not in cooldown
        assert not self.signal_engine._is_in_cooldown(symbol)
        
        # Set cooldown
        self.signal_engine.signal_states[symbol] = SignalState(
            cooldown_until=datetime.now() + timedelta(minutes=30)
        )
        
        # Should be in cooldown
        assert self.signal_engine._is_in_cooldown(symbol)
    
    def test_should_send_alert_new_signal(self):
        """Test alert sending for new signals."""
        signal = Signal(
            id='test_1',
            timestamp=datetime.now(),
            side='LONG',
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward_ratio=2.0,
            net_risk_reward_ratio=1.8,
            why='Test signal',
            metrics={}
        )
        
        # Should send alert for new signal
        assert self.signal_engine.should_send_alert(signal)
    
    def test_should_send_alert_duplicate_signal(self):
        """Test alert sending for duplicate signals."""
        signal = Signal(
            id='test_1',
            timestamp=datetime.now(),
            side='LONG',
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward_ratio=2.0,
            net_risk_reward_ratio=1.8,
            why='Test signal',
            metrics={}
        )
        
        # First signal should be sent
        assert self.signal_engine.should_send_alert(signal)
        
        # Update signal state
        self.signal_engine._update_signal_state('EURUSD', signal)
        
        # Duplicate signal should not be sent
        assert not self.signal_engine.should_send_alert(signal)
    
    def test_should_send_alert_changed_signal(self):
        """Test alert sending for changed signals."""
        signal1 = Signal(
            id='test_1',
            timestamp=datetime.now(),
            side='LONG',
            symbol='EURUSD',
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward_ratio=2.0,
            net_risk_reward_ratio=1.8,
            why='Test signal',
            metrics={}
        )
        
        # Update signal state with first signal
        self.signal_engine._update_signal_state('EURUSD', signal1)
        
        # Create changed signal
        signal2 = Signal(
            id='test_2',
            timestamp=datetime.now(),
            side='LONG',
            symbol='EURUSD',
            entry_price=1.1005,  # Different entry price
            stop_loss=1.0950,
            take_profit=1.1100,
            risk_reward_ratio=2.0,
            net_risk_reward_ratio=1.8,
            why='Test signal',
            metrics={}
        )
        
        # Changed signal should be sent
        assert self.signal_engine.should_send_alert(signal2)


class TestSignalState:
    """Test signal state functionality."""
    
    def test_signal_state_creation(self):
        """Test signal state creation."""
        state = SignalState(
            last_signal_id='test_1',
            last_signal_time=datetime.now(),
            last_entry_price=1.1000,
            last_stop_loss=1.0950,
            last_take_profit=1.1100,
            cooldown_until=datetime.now() + timedelta(minutes=30)
        )
        
        assert state.last_signal_id == 'test_1'
        assert state.last_entry_price == 1.1000
        assert state.cooldown_until is not None
    
    def test_signal_state_defaults(self):
        """Test signal state with default values."""
        state = SignalState()
        
        assert state.last_signal_id is None
        assert state.last_signal_time is None
        assert state.last_entry_price is None
        assert state.last_stop_loss is None
        assert state.last_take_profit is None
        assert state.cooldown_until is None