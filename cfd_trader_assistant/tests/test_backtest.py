"""
Tests for backtesting functionality.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.backtest import BacktestEngine, BacktestResult
from app.signal_engine import SignalEngine
from app.pricing import PricingEngine, FeesModel


class TestBacktestEngine:
    """Test backtesting engine functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'rules': {
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
            },
            'instruments': {
                'instruments': [
                    {
                        'symbol': 'EURUSD',
                        'provider': 'YahooProvider',
                        'yahoo_symbol': 'EURUSD=X',
                        'kind': 'fx',
                        'pip_value': 10.0,
                        'min_step': 0.0001,
                        'ltf_interval': '5m',
                        'htf_interval': '1h'
                    }
                ]
            }
        }
        self.backtest_engine = BacktestEngine(self.config)
    
    def create_sample_data(self, periods=1000, interval='5m'):
        """Create sample OHLCV data for backtesting."""
        dates = pd.date_range(start='2024-01-01', periods=periods, freq=interval)
        
        # Create realistic price data with trend and volatility
        base_price = 1.1000
        trend = np.linspace(0, 0.05, periods)  # 5% upward trend
        noise = np.random.normal(0, 0.001, periods)  # 0.1% volatility
        prices = base_price + trend + noise
        
        # Create OHLCV data
        data = []
        for i, (date, price) in enumerate(zip(dates, prices)):
            # Add some volatility
            volatility = 0.0005
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
    
    def test_backtest_engine_initialization(self):
        """Test backtest engine initialization."""
        assert self.backtest_engine.signal_engine is not None
        assert self.backtest_engine.pricing_engine is not None
        assert self.backtest_engine.fees_model is not None
        assert self.backtest_engine.macro_calendar is not None
    
    def test_load_instruments(self):
        """Test instrument loading."""
        # Instruments should be loaded during initialization
        assert hasattr(self.backtest_engine, 'instruments')
        assert len(self.backtest_engine.instruments) > 0
    
    def test_run_backtest_eod(self):
        """Test EOD backtest execution."""
        # Create sample data
        htf_data = self.create_sample_data(500, '1d')  # Daily data
        ltf_data = self.create_sample_data(500, '1d')  # Same for EOD
        
        # Mock data provider
        def mock_get_ohlcv(symbol, interval, start=None, end=None):
            if interval == '1d':
                return htf_data
            return ltf_data
        
        self.backtest_engine.providers['YahooProvider'].get_ohlcv = mock_get_ohlcv
        
        # Run backtest
        result = self.backtest_engine.run_backtest(
            symbols=['EURUSD'],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 6, 30),
            initial_capital=10000,
            mode='eod'
        )
        
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 10000
        assert result.start_date is not None
        assert result.end_date is not None
    
    def test_run_backtest_intraday(self):
        """Test intraday backtest execution."""
        # Create sample data
        htf_data = self.create_sample_data(100, '1h')  # Hourly data
        ltf_data = self.create_sample_data(1000, '5m')  # 5-minute data
        
        # Mock data provider
        def mock_get_ohlcv(symbol, interval, start=None, end=None):
            if interval == '1h':
                return htf_data
            elif interval == '5m':
                return ltf_data
            return pd.DataFrame()
        
        self.backtest_engine.providers['YahooProvider'].get_ohlcv = mock_get_ohlcv
        
        # Run backtest
        result = self.backtest_engine.run_backtest(
            symbols=['EURUSD'],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),  # One week
            initial_capital=10000,
            mode='intraday'
        )
        
        assert isinstance(result, BacktestResult)
        assert result.initial_capital == 10000
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        # Create sample trades
        trades = [
            {'pnl': 100, 'costs': 5, 'duration': 1},
            {'pnl': -50, 'costs': 3, 'duration': 2},
            {'pnl': 200, 'costs': 8, 'duration': 1},
            {'pnl': -30, 'costs': 2, 'duration': 1}
        ]
        
        result = BacktestResult()
        result.trades = trades
        result.initial_capital = 10000
        
        # Calculate metrics
        self.backtest_engine._calculate_metrics(result)
        
        # Check basic metrics
        assert result.gross_pnl == 220  # 100 - 50 + 200 - 30
        assert result.total_costs == 18  # 5 + 3 + 8 + 2
        assert result.net_pnl == 202  # 220 - 18
        assert result.win_rate == 0.5  # 2 wins out of 4 trades
    
    def test_calculate_equity_curve(self):
        """Test equity curve calculation."""
        # Create sample trades with timestamps
        trades = [
            {
                'entry_time': datetime(2024, 1, 1, 10, 0),
                'exit_time': datetime(2024, 1, 1, 11, 0),
                'pnl': 100,
                'costs': 5
            },
            {
                'entry_time': datetime(2024, 1, 1, 12, 0),
                'exit_time': datetime(2024, 1, 1, 13, 0),
                'pnl': -50,
                'costs': 3
            }
        ]
        
        result = BacktestResult()
        result.trades = trades
        result.initial_capital = 10000
        
        # Calculate equity curve
        equity_curve = self.backtest_engine._calculate_equity_curve(result)
        
        assert not equity_curve.empty
        assert equity_curve.iloc[0]['equity'] == 10000
        assert equity_curve.iloc[-1]['equity'] == 10047  # 10000 + 100 - 5 - 50 - 3
    
    def test_generate_html_report(self):
        """Test HTML report generation."""
        # Create sample result
        result = BacktestResult()
        result.trades = [
            {'pnl': 100, 'costs': 5, 'entry_time': datetime.now(), 'exit_time': datetime.now()}
        ]
        result.initial_capital = 10000
        result.final_capital = 10095
        result.gross_pnl = 100
        result.net_pnl = 95
        result.total_costs = 5
        result.win_rate = 1.0
        result.profit_factor = 2.0
        
        # Generate report
        report_path = self.backtest_engine._generate_html_report(result, 'test_report')
        
        assert report_path is not None
        assert report_path.endswith('.html')
    
    def test_backtest_with_costs(self):
        """Test backtest with transaction costs."""
        # Create sample data
        htf_data = self.create_sample_data(100, '1h')
        ltf_data = self.create_sample_data(1000, '5m')
        
        # Mock data provider
        def mock_get_ohlcv(symbol, interval, start=None, end=None):
            if interval == '1h':
                return htf_data
            elif interval == '5m':
                return ltf_data
            return pd.DataFrame()
        
        self.backtest_engine.providers['YahooProvider'].get_ohlcv = mock_get_ohlcv
        
        # Run backtest
        result = self.backtest_engine.run_backtest(
            symbols=['EURUSD'],
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            initial_capital=10000,
            mode='intraday'
        )
        
        # Check that costs are calculated
        assert hasattr(result, 'gross_pnl')
        assert hasattr(result, 'net_pnl')
        assert hasattr(result, 'total_costs')
        assert result.gross_pnl >= result.net_pnl  # Net should be less than gross due to costs


class TestBacktestResult:
    """Test backtest result functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.result = BacktestResult()
    
    def test_backtest_result_initialization(self):
        """Test backtest result initialization."""
        assert self.result.trades == []
        assert self.result.equity_curve.empty
        assert self.result.metrics == {}
        assert self.result.signals == []
        assert self.result.initial_capital == 0
        assert self.result.final_capital == 0
        assert self.result.gross_pnl == 0.0
        assert self.result.net_pnl == 0.0
        assert self.result.total_costs == 0.0
    
    def test_backtest_result_metrics(self):
        """Test backtest result metrics calculation."""
        # Set up sample data
        self.result.initial_capital = 10000
        self.result.final_capital = 11000
        self.result.gross_pnl = 1200
        self.result.total_costs = 200
        self.result.net_pnl = 1000
        
        # Calculate derived metrics
        self.result.total_return = (self.result.final_capital - self.result.initial_capital) / self.result.initial_capital
        
        assert self.result.total_return == 0.1  # 10% return
        assert self.result.net_pnl == self.result.gross_pnl - self.result.total_costs


class TestBacktestIntegration:
    """Test backtest integration with other components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            'rules': {
                'trend': {'sma_long': 200, 'sma_mid': 50, 'sma_fast': 20},
                'entry': {'donchian_period': 20, 'roc_lookback': 10},
                'quality': {'vol_mult': 1.2, 'atr_min_pct': 0.003, 'atr_max_pct': 0.03},
                'risk': {'stop_atr_mult': 1.5, 'rr_ratio': 2.0},
                'fees': {'spread': 0.0001, 'commission': 0.0001, 'swap_rate': 0.0001}
            }
        }
    
    def test_signal_engine_integration(self):
        """Test integration with signal engine."""
        signal_engine = SignalEngine(self.config['rules'])
        assert signal_engine is not None
        assert signal_engine.config == self.config['rules']
    
    def test_pricing_engine_integration(self):
        """Test integration with pricing engine."""
        pricing_engine = PricingEngine(self.config['rules'])
        assert pricing_engine is not None
        
        # Test price rounding
        rounded_price = pricing_engine.round_price(1.12345, 0.0001)
        assert rounded_price == 1.1235
    
    def test_fees_model_integration(self):
        """Test integration with fees model."""
        fees_model = FeesModel(self.config['rules']['fees'])
        assert fees_model is not None
        
        # Test cost calculation
        total_costs = fees_model.calculate_total_costs(1.0, 10000.0, 10.0, 1)
        assert total_costs > 0
    
    def test_deterministic_backtest(self):
        """Test that backtest produces deterministic results."""
        # This test ensures that the same input produces the same output
        # which is important for reproducible backtesting
        
        # Create deterministic sample data
        np.random.seed(42)  # Fixed seed for reproducibility
        
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        prices = 1.1000 + np.cumsum(np.random.normal(0, 0.001, 100))
        
        data = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': prices * 1.001,
            'low': prices * 0.999,
            'close': prices,
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Run backtest twice with same data
        engine1 = BacktestEngine(self.config)
        engine2 = BacktestEngine(self.config)
        
        # Mock data provider for both engines
        def mock_get_ohlcv(symbol, interval, start=None, end=None):
            return data
        
        engine1.providers['YahooProvider'].get_ohlcv = mock_get_ohlcv
        engine2.providers['YahooProvider'].get_ohlcv = mock_get_ohlcv
        
        # Run backtests
        result1 = engine1.run_backtest(['EURUSD'], datetime(2024, 1, 1), datetime(2024, 1, 5), 10000, 'intraday')
        result2 = engine2.run_backtest(['EURUSD'], datetime(2024, 1, 1), datetime(2024, 1, 5), 10000, 'intraday')
        
        # Results should be identical
        assert result1.final_capital == result2.final_capital
        assert result1.gross_pnl == result2.gross_pnl
        assert result1.net_pnl == result2.net_pnl
        assert len(result1.trades) == len(result2.trades)