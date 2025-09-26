import argparse
import sys
from pathlib import Path

from cfd_trader_assistant.app.scheduler import run_scanner_once, run_scheduler
from cfd_trader_assistant.app.backtest import run_backtest_preset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CFD Trader Assistant CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="Run market scan")
    scan.add_argument("--mode", choices=["intraday", "eod"], required=True)
    scan.add_argument("--once", action="store_true", help="Run once and exit")

    bt = subparsers.add_parser("backtest", help="Run backtest preset")
    bt.add_argument("--preset", choices=["eod_spy_qqq", "intraday_nas100_sample"], required=True)

    subparsers.add_parser("dashboard", help="Launch Streamlit dashboard")

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "scan":
        if args.once:
            run_scanner_once(mode=args.mode)
        else:
            run_scheduler(mode=args.mode)
        return 0
    if args.command == "backtest":
        run_backtest_preset(args.preset)
        return 0
    if args.command == "dashboard":
        # Defer import - streamlit friendly
        import subprocess

        dashboard_path = Path(__file__).parent / "cfd_trader_assistant" / "app" / "dashboard.py"
        subprocess.run(["streamlit", "run", str(dashboard_path)], check=False)
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
