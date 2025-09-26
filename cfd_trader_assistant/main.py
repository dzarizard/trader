"""
Main CLI for CFD Trader Assistant.
"""
import argparse
import sys
import os
import logging
import yaml
from datetime import datetime, timedelta
from typing import Dict, Any

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.scheduler import TradingScheduler
from app.backtest import run_preset_backtest
from app.dashboard import main as dashboard_main

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cfd_trader.log')
    ]
)

logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load configuration from files."""
    try:
        with open('config/rules.yaml', 'r') as f:
            rules_config = yaml.safe_load(f)
        
        with open('config/account.yaml', 'r') as f:
            account_config = yaml.safe_load(f)
        
        return {
            'rules': rules_config,
            'account': account_config
        }
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def scan_mode(args):
    """Run in scanning mode."""
    logger.info(f"Starting CFD Trader Assistant in {args.mode} mode")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return 1
    
    # Initialize scheduler
    scheduler = TradingScheduler(config)
    
    try:
        if args.mode == 'intraday':
            logger.info("Running intraday scanning mode")
            # Run one scan immediately
            scheduler.scan_intraday()
            
            # Start scheduler for continuous scanning
            scheduler.start()
            
            # Keep running
            try:
                while True:
                    import time
                    time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                scheduler.stop()
        
        elif args.mode == 'eod':
            logger.info("Running EOD scanning mode")
            # Run EOD scan
            scheduler.scan_eod()
        
        else:
            logger.error(f"Unknown mode: {args.mode}")
            return 1
    
    except Exception as e:
        logger.error(f"Error in scan mode: {e}")
        return 1
    
    return 0


def backtest_mode(args):
    """Run backtest mode."""
    logger.info(f"Running backtest with preset: {args.preset}")
    
    try:
        # Run backtest
        result = run_preset_backtest(args.preset)
        
        # Print results
        print("\n" + "="*50)
        print("BACKTEST RESULTS")
        print("="*50)
        print(f"Period: {result.start_date.strftime('%Y-%m-%d')} to {result.end_date.strftime('%Y-%m-%d')}")
        print(f"Initial Capital: ${result.initial_capital:,.2f}")
        print(f"Final Capital: ${result.final_capital:,.2f}")
        print(f"Total Return: {result.total_return:.2f}%")
        print(f"Total Trades: {result.metrics.get('total_trades', 0)}")
        print(f"Win Rate: {result.metrics.get('win_rate', 0):.1f}%")
        print(f"Profit Factor: {result.metrics.get('profit_factor', 0):.2f}")
        print(f"Max Drawdown: {result.metrics.get('max_drawdown', 0):.2f}%")
        print(f"Sharpe Ratio: {result.metrics.get('sharpe_ratio', 0):.2f}")
        print("="*50)
        
        # Show recent trades
        if result.trades:
            print("\nRecent Trades:")
            print("-" * 80)
            for trade in result.trades[-5:]:  # Show last 5 trades
                pnl_str = f"${trade['pnl']:.2f}"
                pnl_color = "+" if trade['pnl'] > 0 else ""
                print(f"{trade['entry_time'].strftime('%Y-%m-%d %H:%M')} | "
                      f"{trade['side']} {trade['symbol']} | "
                      f"Entry: {trade['entry_price']:.4f} | "
                      f"Exit: {trade['exit_price']:.4f} | "
                      f"P&L: {pnl_color}{pnl_str} | "
                      f"Reason: {trade['exit_reason']}")
        
        print(f"\nDetailed report saved to: backtest_report_{args.preset}.html")
        print(f"Trades CSV saved to: backtest_trades_{args.preset}.csv")
        
    except Exception as e:
        logger.error(f"Error in backtest mode: {e}")
        return 1
    
    return 0


def dashboard_mode(args):
    """Run dashboard mode."""
    logger.info("Starting Streamlit dashboard")
    
    try:
        # Import and run Streamlit dashboard
        import subprocess
        import sys
        
        # Run streamlit
        cmd = [sys.executable, "-m", "streamlit", "run", "app/dashboard.py", "--server.port", str(args.port)]
        if args.host:
            cmd.extend(["--server.address", args.host])
        
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"Error starting dashboard: {e}")
        return 1
    
    return 0


def status_mode(args):
    """Show system status."""
    logger.info("Checking system status")
    
    try:
        # Load configuration
        config = load_config()
        if not config:
            logger.error("Failed to load configuration")
            return 1
        
        # Initialize scheduler to get status
        scheduler = TradingScheduler(config)
        
        # Get status
        status = scheduler.get_status()
        portfolio = scheduler.get_portfolio_summary()
        active_signals = scheduler.get_active_signals()
        
        print("\n" + "="*50)
        print("CFD TRADER ASSISTANT STATUS")
        print("="*50)
        print(f"Status: {'🟢 Running' if status['running'] else '🔴 Stopped'}")
        print(f"Account Equity: ${status['account_equity']:,.2f}")
        print(f"Daily P&L: ${status['daily_pnl']:,.2f}")
        print(f"Active Positions: {status['active_positions']}")
        print(f"Active Signals: {status['active_signals']}")
        
        if status['next_job']:
            print(f"Next Scheduled Job: {status['next_job']}")
        
        print("\nPortfolio Summary:")
        print(f"  Total Exposure: ${portfolio.get('total_exposure', 0):,.2f}")
        print(f"  Total Risk: ${portfolio.get('total_risk', 0):,.2f}")
        print(f"  Win Rate: {portfolio.get('win_rate', 0):.1f}%")
        print(f"  Daily Trades: {portfolio.get('daily_trades', 0)}")
        
        if active_signals:
            print("\nActive Signals:")
            print("-" * 60)
            for signal in active_signals:
                print(f"  {signal.side} {signal.symbol} @ {signal.entry_price:.4f} "
                      f"(SL: {signal.stop_loss:.4f}, TP: {signal.take_profit:.4f})")
        
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        return 1
    
    return 0


def test_mode(args):
    """Run system tests."""
    logger.info("Running system tests")
    
    try:
        # Test configuration loading
        print("Testing configuration loading...")
        config = load_config()
        if config:
            print("✅ Configuration loaded successfully")
        else:
            print("❌ Configuration loading failed")
            return 1
        
        # Test providers
        print("Testing data providers...")
        from app.providers.yahoo import YahooProvider
        from app.providers.stooq import StooqProvider
        
        yahoo_provider = YahooProvider({})
        stooq_provider = StooqProvider({})
        
        print("✅ Data providers initialized")
        
        # Test indicators
        print("Testing technical indicators...")
        import pandas as pd
        import numpy as np
        from app.indicators import compute_indicators
        
        # Create sample data
        dates = pd.date_range(start='2024-01-01', end='2024-01-31', freq='D')
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
        
        sample_data = pd.DataFrame({
            'open': prices,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        })
        
        indicators = compute_indicators(sample_data, config.get('rules', {}))
        if indicators:
            print("✅ Technical indicators computed successfully")
        else:
            print("❌ Technical indicators computation failed")
            return 1
        
        # Test signal generation
        print("Testing signal generation...")
        from app.rules import SignalGenerator
        
        signal_generator = SignalGenerator(config.get('rules', {}))
        signals = signal_generator.generate_signals(sample_data, sample_data, 'TEST')
        
        print(f"✅ Signal generation test completed ({len(signals)} signals generated)")
        
        # Test alert system
        print("Testing alert system...")
        from app.alerts import AlertManager
        
        alert_manager = AlertManager(config.get('account', {}))
        alert_status = alert_manager.get_alert_status()
        
        print("✅ Alert system initialized")
        print(f"  Telegram: {'✅' if alert_status['telegram']['configured'] else '❌'}")
        print(f"  Slack: {'✅' if alert_status['slack']['configured'] else '❌'}")
        print(f"  Email: {'✅' if alert_status['email']['configured'] else '❌'}")
        
        print("\n🎉 All tests passed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test mode: {e}")
        print(f"❌ Test failed: {e}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CFD Trader Assistant - Automated Trading Signal Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py scan --mode=intraday    # Run intraday scanning
  python main.py scan --mode=eod         # Run EOD scanning
  python main.py backtest --preset=eod_spy_qqq  # Run backtest
  python main.py dashboard               # Start web dashboard
  python main.py status                  # Show system status
  python main.py test                    # Run system tests

⚠️  WARNING: This is not investment advice. CFD trading involves high risk.
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Run market scanning')
    scan_parser.add_argument('--mode', choices=['intraday', 'eod'], required=True,
                           help='Scanning mode')
    
    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--preset', 
                               choices=['eod_spy_qqq', 'intraday_nas100', 'fx_major_pairs'],
                               required=True,
                               help='Backtest preset to run')
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser('dashboard', help='Start web dashboard')
    dashboard_parser.add_argument('--port', type=int, default=8501,
                                help='Dashboard port (default: 8501)')
    dashboard_parser.add_argument('--host', type=str, default='0.0.0.0',
                                help='Dashboard host (default: 0.0.0.0)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Show system status')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Run system tests')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Show warning
    print("⚠️  WARNING: This is not investment advice. CFD trading involves high risk.")
    print("=" * 70)
    
    # Route to appropriate mode
    if args.command == 'scan':
        return scan_mode(args)
    elif args.command == 'backtest':
        return backtest_mode(args)
    elif args.command == 'dashboard':
        return dashboard_mode(args)
    elif args.command == 'status':
        return status_mode(args)
    elif args.command == 'test':
        return test_mode(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())