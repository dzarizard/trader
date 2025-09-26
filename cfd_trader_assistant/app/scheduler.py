"""
Scheduler for CFD Trader Assistant.
Handles periodic scanning and signal generation.
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
import yaml
import os
from pathlib import Path

from .providers.yahoo import YahooProvider
from .providers.stooq import StooqProvider
from .indicators import compute_indicators
from .rules import SignalGenerator, SignalManager
from .macro import TimeFilter
from .sizing import Account, Instrument, PositionSizer, RiskManager
from .alerts import AlertManager

logger = logging.getLogger(__name__)


class TradingScheduler:
    """Main trading scheduler."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.running = False
        self.thread = None
        
        # Initialize components
        self.load_configs()
        self.initialize_components()
        
        # Schedule jobs
        self.setup_schedule()
    
    def load_configs(self):
        """Load configuration files."""
        try:
            # Load instruments
            with open('config/instruments.yaml', 'r') as f:
                self.instruments_config = yaml.safe_load(f)
            
            # Load rules
            with open('config/rules.yaml', 'r') as f:
                self.rules_config = yaml.safe_load(f)
            
            # Load account
            with open('config/account.yaml', 'r') as f:
                self.account_config = yaml.safe_load(f)
            
            # Load macro
            with open('config/macro.yaml', 'r') as f:
                self.macro_config = yaml.safe_load(f)
                
        except Exception as e:
            logger.error(f"Error loading configs: {e}")
            self.instruments_config = {}
            self.rules_config = {}
            self.account_config = {}
            self.macro_config = {}
    
    def initialize_components(self):
        """Initialize trading components."""
        try:
            # Initialize providers
            self.providers = {
                'YahooProvider': YahooProvider({}),
                'StooqProvider': StooqProvider({})
            }
            
            # Initialize instruments
            self.instruments = {}
            for instr_config in self.instruments_config.get('instruments', []):
                self.instruments[instr_config['symbol']] = Instrument(instr_config)
            
            # Initialize trading components
            self.signal_generator = SignalGenerator(self.rules_config)
            self.signal_manager = SignalManager(self.rules_config)
            self.time_filter = TimeFilter(
                macro_config_path='config/macro.yaml',
                instruments_config=self.instruments_config
            )
            
            # Initialize account and risk management
            self.account = Account(self.account_config)
            self.risk_manager = RiskManager(self.account)
            self.position_sizer = PositionSizer(self.account)
            
            # Initialize alert manager
            self.alert_manager = AlertManager(self.account_config)
            
            logger.info("Trading components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
    
    def setup_schedule(self):
        """Setup scheduled jobs."""
        try:
            # Clear existing jobs
            schedule.clear()
            
            # Intraday scanning (every 5 minutes during market hours)
            schedule.every(5).minutes.do(self.scan_intraday)
            
            # EOD scanning (after market close)
            schedule.every().day.at("16:30").do(self.scan_eod)
            
            # Daily cleanup (midnight)
            schedule.every().day.at("00:00").do(self.daily_cleanup)
            
            # Weekly report (Monday morning)
            schedule.every().monday.at("09:00").do(self.weekly_report)
            
            logger.info("Schedule setup completed")
            
        except Exception as e:
            logger.error(f"Error setting up schedule: {e}")
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        
        logger.info("Trading scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        
        logger.info("Trading scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(5)
    
    def scan_intraday(self):
        """Perform intraday market scan."""
        try:
            logger.info("Starting intraday scan")
            
            # Get current time
            current_time = datetime.now()
            
            # Scan each instrument
            for symbol, instrument in self.instruments.items():
                try:
                    # Check if trading is allowed
                    can_trade = self.time_filter.can_trade(
                        symbol=symbol,
                        current_time=current_time,
                        macro_config=self.rules_config.get('filters', {}).get('macro', {})
                    )
                    
                    if not can_trade['can_trade']:
                        logger.debug(f"Trading not allowed for {symbol}: {can_trade['reasons']}")
                        continue
                    
                    # Get data
                    data = self._get_instrument_data(symbol, instrument, mode='intraday')
                    if not data:
                        continue
                    
                    # Generate signals
                    signals = self._generate_signals(symbol, instrument, data)
                    
                    # Process signals
                    for signal in signals:
                        self._process_signal(signal, instrument)
                    
                    # Update existing positions
                    self._update_positions(symbol, data)
                    
                except Exception as e:
                    logger.error(f"Error scanning {symbol}: {e}")
            
            logger.info("Intraday scan completed")
            
        except Exception as e:
            logger.error(f"Error in intraday scan: {e}")
    
    def scan_eod(self):
        """Perform end-of-day market scan."""
        try:
            logger.info("Starting EOD scan")
            
            # Get current time
            current_time = datetime.now()
            
            # Scan each instrument
            for symbol, instrument in self.instruments.items():
                try:
                    # Get EOD data
                    data = self._get_instrument_data(symbol, instrument, mode='eod')
                    if not data:
                        continue
                    
                    # Generate signals
                    signals = self._generate_signals(symbol, instrument, data)
                    
                    # Process signals
                    for signal in signals:
                        self._process_signal(signal, instrument)
                    
                    # Update existing positions
                    self._update_positions(symbol, data)
                    
                except Exception as e:
                    logger.error(f"Error in EOD scan for {symbol}: {e}")
            
            # Generate daily report
            self._generate_daily_report()
            
            logger.info("EOD scan completed")
            
        except Exception as e:
            logger.error(f"Error in EOD scan: {e}")
    
    def daily_cleanup(self):
        """Perform daily cleanup tasks."""
        try:
            logger.info("Starting daily cleanup")
            
            # Reset daily statistics
            self.account.reset_daily_stats()
            
            # Clean up old signals
            self._cleanup_old_signals()
            
            # Update account equity
            self._update_account_equity()
            
            logger.info("Daily cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")
    
    def weekly_report(self):
        """Generate weekly performance report."""
        try:
            logger.info("Generating weekly report")
            
            # Get portfolio summary
            portfolio_summary = self.risk_manager.get_portfolio_summary()
            
            # Create report
            report = {
                'week_ending': datetime.now().strftime('%Y-%m-%d'),
                'account_equity': portfolio_summary.get('account_equity', 0),
                'weekly_pnl': portfolio_summary.get('total_pnl', 0),
                'active_positions': portfolio_summary.get('active_positions', 0),
                'win_rate': portfolio_summary.get('win_rate', 0),
                'total_trades': portfolio_summary.get('daily_trades', 0)
            }
            
            # Send report via alerts
            self.alert_manager.send_warning_alert(
                title="Weekly Performance Report",
                content=f"Account Equity: ${report['account_equity']:.2f}\n"
                       f"Weekly P&L: ${report['weekly_pnl']:.2f}\n"
                       f"Active Positions: {report['active_positions']}\n"
                       f"Win Rate: {report['win_rate']:.1f}%\n"
                       f"Total Trades: {report['total_trades']}",
                symbol="SYSTEM"
            )
            
            logger.info("Weekly report generated")
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
    
    def _get_instrument_data(self, symbol: str, instrument: Instrument, mode: str) -> Optional[Dict[str, pd.DataFrame]]:
        """Get data for an instrument."""
        try:
            provider_name = instrument.config.get('provider', 'YahooProvider')
            provider = self.providers.get(provider_name)
            
            if not provider:
                logger.warning(f"Provider {provider_name} not available for {symbol}")
                return None
            
            # Get data based on mode
            if mode == 'intraday':
                interval = instrument.config.get('ltf_interval', '5m')
                limit = 200  # Get enough data for indicators
            else:  # EOD
                interval = '1d'
                limit = 200
            
            # Fetch data
            df = provider.get_ohlcv(
                symbol=instrument.config.get('yahoo_symbol', symbol),
                interval=interval,
                limit=limit
            )
            
            if df.empty:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Compute indicators
            indicators = compute_indicators(df, self.rules_config)
            
            return {
                'htf': df,  # For simplicity, use same data for both timeframes
                'ltf': df,
                'indicators': indicators
            }
            
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            return None
    
    def _generate_signals(self, symbol: str, instrument: Instrument, data: Dict[str, Any]) -> List:
        """Generate signals for an instrument."""
        try:
            # Check macro filter
            macro_guard = self.time_filter.can_trade(
                symbol=symbol,
                macro_config=self.rules_config.get('filters', {}).get('macro', {})
            )
            
            # Generate signals
            signals = self.signal_generator.generate_signals(
                htf_df=data['htf'],
                ltf_df=data['ltf'],
                symbol=symbol,
                macro_guard=macro_guard
            )
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []
    
    def _process_signal(self, signal, instrument: Instrument):
        """Process a generated signal."""
        try:
            # Validate signal with risk manager
            is_valid, reason = self.risk_manager.validate_signal(signal, instrument)
            if not is_valid:
                logger.debug(f"Signal rejected for {signal.symbol}: {reason}")
                return
            
            # Calculate position size
            position_plan = self.position_sizer.calculate_position_size(signal, instrument)
            
            # Add to signal manager
            if self.signal_manager.add_signal(signal):
                # Add position to risk manager
                self.risk_manager.add_position(signal, position_plan, instrument)
                
                # Send alert
                self.alert_manager.send_signal_alert(signal, position_plan, instrument.config)
                
                logger.info(f"Signal processed for {signal.symbol}: {signal.side}")
            else:
                logger.warning(f"Failed to add signal for {signal.symbol}")
                
        except Exception as e:
            logger.error(f"Error processing signal for {signal.symbol}: {e}")
    
    def _update_positions(self, symbol: str, data: Dict[str, Any]):
        """Update existing positions for a symbol."""
        try:
            if data and 'ltf' in data and not data['ltf'].empty:
                current_price = data['ltf']['close'].iloc[-1]
                
                # Update positions in risk manager
                closed_positions = self.risk_manager.update_positions({symbol: current_price})
                
                # Send exit alerts for closed positions
                for position in closed_positions:
                    signal = position['signal']
                    exit_reason = position['exit_reason']
                    final_pnl = position['final_pnl']
                    
                    self.alert_manager.send_exit_alert(signal, exit_reason, final_pnl)
                    
                    logger.info(f"Position closed for {signal.symbol}: {exit_reason}, P&L: ${final_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating positions for {symbol}: {e}")
    
    def _cleanup_old_signals(self):
        """Clean up old signals."""
        try:
            # Remove signals older than 7 days
            cutoff_date = datetime.now() - timedelta(days=7)
            
            # This would be implemented based on your signal storage mechanism
            logger.info("Old signals cleanup completed")
            
        except Exception as e:
            logger.error(f"Error cleaning up old signals: {e}")
    
    def _update_account_equity(self):
        """Update account equity based on current positions."""
        try:
            portfolio_summary = self.risk_manager.get_portfolio_summary()
            current_equity = portfolio_summary.get('account_equity', self.account.equity)
            
            # Update account equity
            self.account.equity = current_equity
            
            logger.info(f"Account equity updated: ${current_equity:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating account equity: {e}")
    
    def _generate_daily_report(self):
        """Generate daily performance report."""
        try:
            portfolio_summary = self.risk_manager.get_portfolio_summary()
            
            # Create daily report
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'account_equity': portfolio_summary.get('account_equity', 0),
                'daily_pnl': portfolio_summary.get('daily_pnl', 0),
                'active_positions': portfolio_summary.get('active_positions', 0),
                'total_trades': portfolio_summary.get('daily_trades', 0),
                'win_rate': portfolio_summary.get('win_rate', 0)
            }
            
            logger.info(f"Daily report: {report}")
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            'running': self.running,
            'next_job': str(schedule.next_run()) if schedule.jobs else None,
            'active_signals': len(self.signal_manager.get_active_signals()),
            'account_equity': self.account.equity,
            'daily_pnl': self.account.daily_pnl,
            'active_positions': len(self.risk_manager.active_positions)
        }
    
    def force_scan(self):
        """Force an immediate scan."""
        try:
            logger.info("Forcing immediate scan")
            self.scan_intraday()
        except Exception as e:
            logger.error(f"Error in forced scan: {e}")
    
    def get_active_signals(self) -> List:
        """Get all active signals."""
        return self.signal_manager.get_active_signals()
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary."""
        return self.risk_manager.get_portfolio_summary()