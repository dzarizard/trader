"""
Backtesting system for CFD Trader Assistant.
"""
import pandas as pd
import numpy as np
import vectorbt as vbt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging
import json
import os
from pathlib import Path

from .providers.yahoo import YahooProvider
from .providers.stooq import StooqProvider
from .indicators import compute_indicators
from .rules import SignalGenerator, SignalManager
from .macro import TimeFilter
from .sizing import Account, Instrument, PositionSizer, RiskManager

logger = logging.getLogger(__name__)


class BacktestResult:
    """Backtest result container."""
    
    def __init__(self):
        self.trades = []
        self.equity_curve = pd.DataFrame()
        self.metrics = {}
        self.signals = []
        self.start_date = None
        self.end_date = None
        self.initial_capital = 0
        self.final_capital = 0
        self.total_return = 0
        self.max_drawdown = 0
        self.sharpe_ratio = 0
        self.win_rate = 0
        self.profit_factor = 0


class BacktestEngine:
    """Main backtesting engine."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.signal_generator = SignalGenerator(config)
        self.signal_manager = SignalManager(config)
        self.time_filter = TimeFilter()
        
        # Initialize providers
        self.providers = {
            'YahooProvider': YahooProvider({}),
            'StooqProvider': StooqProvider({})
        }
        
        # Load instruments
        self.load_instruments()
    
    def load_instruments(self):
        """Load instrument configurations."""
        try:
            import yaml
            with open('config/instruments.yaml', 'r') as f:
                instruments_config = yaml.safe_load(f)
            
            self.instruments = {}
            for instr_config in instruments_config.get('instruments', []):
                self.instruments[instr_config['symbol']] = Instrument(instr_config)
                
        except Exception as e:
            logger.error(f"Error loading instruments: {e}")
            self.instruments = {}
    
    def run_backtest(
        self,
        symbols: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000,
        mode: str = 'eod'
    ) -> BacktestResult:
        """
        Run backtest for specified symbols and date range.
        
        Args:
            symbols: List of symbols to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Initial capital
            mode: 'eod' or 'intraday'
            
        Returns:
            BacktestResult object
        """
        logger.info(f"Starting backtest for {symbols} from {start_date} to {end_date}")
        
        result = BacktestResult()
        result.start_date = start_date
        result.end_date = end_date
        result.initial_capital = initial_capital
        
        # Initialize account and risk manager
        account = Account({'initial_equity': initial_capital})
        risk_manager = RiskManager(account)
        position_sizer = PositionSizer(account)
        
        # Get data for all symbols
        data = self._get_backtest_data(symbols, start_date, end_date, mode)
        
        if not data:
            logger.error("No data available for backtest")
            return result
        
        # Run backtest
        equity_curve = []
        current_equity = initial_capital
        
        for date in pd.date_range(start=start_date, end=end_date, freq='D'):
            if date not in data:
                continue
            
            # Generate signals for this date
            signals = self._generate_signals_for_date(data[date], date)
            
            # Process signals
            for signal in signals:
                if signal.symbol in self.instruments:
                    instrument = self.instruments[signal.symbol]
                    
                    # Validate signal
                    is_valid, reason = risk_manager.validate_signal(signal, instrument)
                    if not is_valid:
                        logger.debug(f"Signal rejected for {signal.symbol}: {reason}")
                        continue
                    
                    # Calculate position size
                    position_plan = position_sizer.calculate_position_size(signal, instrument)
                    
                    # Add position
                    risk_manager.add_position(signal, position_plan, instrument)
                    result.signals.append(signal)
            
            # Update positions with current prices
            current_prices = {symbol: df['close'].iloc[-1] for symbol, df in data[date].items()}
            closed_positions = risk_manager.update_positions(current_prices)
            
            # Record closed trades
            for position in closed_positions:
                trade = {
                    'entry_time': position['entry_time'],
                    'exit_time': position['exit_time'],
                    'symbol': position['signal'].symbol,
                    'side': position['signal'].side,
                    'entry_price': position['signal'].entry_price,
                    'exit_price': current_prices.get(position['signal'].symbol, 0),
                    'size': position['position_plan'].size_units,
                    'pnl': position['final_pnl'],
                    'exit_reason': position['exit_reason']
                }
                result.trades.append(trade)
            
            # Update equity
            portfolio_summary = risk_manager.get_portfolio_summary()
            current_equity = initial_capital + portfolio_summary.get('total_pnl', 0)
            equity_curve.append({
                'date': date,
                'equity': current_equity,
                'drawdown': (current_equity - initial_capital) / initial_capital * 100
            })
        
        # Calculate final results
        result.equity_curve = pd.DataFrame(equity_curve)
        result.final_capital = current_equity
        result.total_return = (current_equity - initial_capital) / initial_capital * 100
        
        # Calculate metrics
        result.metrics = self._calculate_metrics(result)
        
        logger.info(f"Backtest completed. Final capital: ${current_equity:.2f}, Return: {result.total_return:.2f}%")
        
        return result
    
    def _get_backtest_data(self, symbols: List[str], start_date: datetime, end_date: datetime, mode: str) -> Dict[datetime, Dict[str, pd.DataFrame]]:
        """Get historical data for backtest."""
        data = {}
        
        for symbol in symbols:
            if symbol not in self.instruments:
                logger.warning(f"No instrument config for {symbol}")
                continue
            
            instrument = self.instruments[symbol]
            provider_name = instrument.config.get('provider', 'YahooProvider')
            
            if provider_name not in self.providers:
                logger.warning(f"Provider {provider_name} not available")
                continue
            
            provider = self.providers[provider_name]
            
            try:
                if mode == 'eod':
                    # Get daily data
                    df = provider.get_ohlcv(
                        symbol=instrument.config.get('yahoo_symbol', symbol),
                        interval='1d',
                        start=start_date,
                        end=end_date
                    )
                else:
                    # Get intraday data
                    df = provider.get_ohlcv(
                        symbol=instrument.config.get('yahoo_symbol', symbol),
                        interval=instrument.config.get('ltf_interval', '5m'),
                        start=start_date,
                        end=end_date
                    )
                
                if df.empty:
                    logger.warning(f"No data for {symbol}")
                    continue
                
                # Group by date for daily processing
                df['date'] = pd.to_datetime(df['timestamp']).dt.date
                
                for date, group in df.groupby('date'):
                    date_dt = pd.to_datetime(date)
                    if date_dt not in data:
                        data[date_dt] = {}
                    data[date_dt][symbol] = group.reset_index(drop=True)
                
                logger.info(f"Loaded {len(df)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Error loading data for {symbol}: {e}")
        
        return data
    
    def _generate_signals_for_date(self, daily_data: Dict[str, pd.DataFrame], date: datetime) -> List:
        """Generate signals for a specific date."""
        signals = []
        
        for symbol, df in daily_data.items():
            if symbol not in self.instruments:
                continue
            
            instrument = self.instruments[symbol]
            
            # Get HTF and LTF data
            htf_interval = instrument.config.get('htf_interval', '1h')
            ltf_interval = instrument.config.get('ltf_interval', '5m')
            
            # For simplicity, use the same data for both timeframes in this example
            # In a real implementation, you'd fetch different timeframes
            
            if len(df) < 200:  # Need enough data for indicators
                continue
            
            # Generate signals
            symbol_signals = self.signal_generator.generate_signals(
                htf_df=df,
                ltf_df=df,
                symbol=symbol
            )
            
            signals.extend(symbol_signals)
        
        return signals
    
    def _calculate_metrics(self, result: BacktestResult) -> Dict[str, float]:
        """Calculate backtest performance metrics."""
        if not result.trades:
            return {}
        
        trades_df = pd.DataFrame(result.trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # P&L metrics
        total_pnl = trades_df['pnl'].sum()
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0
        
        # Profit factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Drawdown calculation
        equity_curve = result.equity_curve
        if not equity_curve.empty:
            equity_curve['peak'] = equity_curve['equity'].cummax()
            equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak'] * 100
            max_drawdown = equity_curve['drawdown'].min()
        else:
            max_drawdown = 0
        
        # Sharpe ratio (simplified)
        if not equity_curve.empty and len(equity_curve) > 1:
            returns = equity_curve['equity'].pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((100 - win_rate) / 100 * avg_loss)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'expectancy': expectancy,
            'total_return_pct': result.total_return
        }


class BacktestReport:
    """Generate backtest reports."""
    
    def __init__(self, result: BacktestResult):
        self.result = result
    
    def generate_html_report(self, output_path: str = "backtest_report.html"):
        """Generate HTML backtest report."""
        try:
            html_content = self._create_html_report()
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML report generated: {output_path}")
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
    
    def _create_html_report(self) -> str:
        """Create HTML report content."""
        metrics = self.result.metrics
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CFD Trader Assistant - Backtest Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #1f77b4; color: white; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
                .metric {{ background-color: #f0f2f6; padding: 15px; border-radius: 5px; text-align: center; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #1f77b4; }}
                .metric-label {{ font-size: 14px; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .positive {{ color: #28a745; }}
                .negative {{ color: #dc3545; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CFD Trader Assistant - Backtest Report</h1>
                <p>Period: {self.result.start_date.strftime('%Y-%m-%d')} to {self.result.end_date.strftime('%Y-%m-%d')}</p>
            </div>
            
            <div class="warning">
                <strong>⚠️ WARNING:</strong> This is not investment advice. CFD trading involves high risk. 
                Past performance does not guarantee future results.
            </div>
            
            <div class="section">
                <h2>Performance Summary</h2>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">${self.result.final_capital:.2f}</div>
                        <div class="metric-label">Final Capital</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value {'positive' if self.result.total_return > 0 else 'negative'}">{self.result.total_return:.2f}%</div>
                        <div class="metric-label">Total Return</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                        <div class="metric-label">Total Trades</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('win_rate', 0):.1f}%</div>
                        <div class="metric-label">Win Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('profit_factor', 0):.2f}</div>
                        <div class="metric-label">Profit Factor</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('max_drawdown', 0):.2f}%</div>
                        <div class="metric-label">Max Drawdown</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                        <div class="metric-label">Sharpe Ratio</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics.get('expectancy', 0):.2f}</div>
                        <div class="metric-label">Expectancy</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Trade Details</h2>
                <table>
                    <tr>
                        <th>Entry Time</th>
                        <th>Exit Time</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Entry Price</th>
                        <th>Exit Price</th>
                        <th>Size</th>
                        <th>P&L</th>
                        <th>Exit Reason</th>
                    </tr>
        """
        
        # Add trade rows
        for trade in self.result.trades:
            pnl_class = 'positive' if trade['pnl'] > 0 else 'negative'
            html += f"""
                    <tr>
                        <td>{trade['entry_time'].strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade['exit_time'].strftime('%Y-%m-%d %H:%M')}</td>
                        <td>{trade['symbol']}</td>
                        <td>{trade['side']}</td>
                        <td>{trade['entry_price']:.4f}</td>
                        <td>{trade['exit_price']:.4f}</td>
                        <td>{trade['size']:.2f}</td>
                        <td class="{pnl_class}">${trade['pnl']:.2f}</td>
                        <td>{trade['exit_reason']}</td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Risk Metrics</h2>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">${metrics.get('avg_win', 0):.2f}</div>
                        <div class="metric-label">Average Win</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics.get('avg_loss', 0):.2f}</div>
                        <div class="metric-label">Average Loss</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('winning_trades', 0)}</div>
                        <div class="metric-label">Winning Trades</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{metrics.get('losing_trades', 0)}</div>
                        <div class="metric-label">Losing Trades</div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Backtest Information</h2>
                <p><strong>Initial Capital:</strong> ${self.result.initial_capital:,.2f}</p>
                <p><strong>Final Capital:</strong> ${self.result.final_capital:,.2f}</p>
                <p><strong>Total Return:</strong> {self.result.total_return:.2f}%</p>
                <p><strong>Backtest Period:</strong> {self.result.start_date.strftime('%Y-%m-%d')} to {self.result.end_date.strftime('%Y-%m-%d')}</p>
                <p><strong>Report Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def save_trades_csv(self, output_path: str = "backtest_trades.csv"):
        """Save trades to CSV file."""
        try:
            if self.result.trades:
                trades_df = pd.DataFrame(self.result.trades)
                trades_df.to_csv(output_path, index=False)
                logger.info(f"Trades saved to CSV: {output_path}")
            else:
                logger.warning("No trades to save")
                
        except Exception as e:
            logger.error(f"Error saving trades CSV: {e}")


def run_preset_backtest(preset: str) -> BacktestResult:
    """Run predefined backtest scenarios."""
    
    presets = {
        'eod_spy_qqq': {
            'symbols': ['SPY', 'QQQ'],
            'start_date': datetime(2020, 1, 1),
            'end_date': datetime(2024, 1, 1),
            'mode': 'eod',
            'initial_capital': 10000
        },
        'intraday_nas100': {
            'symbols': ['NAS100'],
            'start_date': datetime(2023, 1, 1),
            'end_date': datetime(2024, 1, 1),
            'mode': 'intraday',
            'initial_capital': 10000
        },
        'fx_major_pairs': {
            'symbols': ['EURUSD', 'GBPUSD'],
            'start_date': datetime(2022, 1, 1),
            'end_date': datetime(2024, 1, 1),
            'mode': 'eod',
            'initial_capital': 10000
        }
    }
    
    if preset not in presets:
        raise ValueError(f"Unknown preset: {preset}. Available: {list(presets.keys())}")
    
    config = presets[preset]
    
    # Load rules config
    try:
        import yaml
        with open('config/rules.yaml', 'r') as f:
            rules_config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading rules config: {e}")
        rules_config = {}
    
    # Run backtest
    engine = BacktestEngine(rules_config)
    result = engine.run_backtest(**config)
    
    # Generate report
    report = BacktestReport(result)
    report.generate_html_report(f"backtest_report_{preset}.html")
    report.save_trades_csv(f"backtest_trades_{preset}.csv")
    
    return result