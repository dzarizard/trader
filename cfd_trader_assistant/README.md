# CFD Trader Assistant

A comprehensive Python-based trading signal generator for CFD (Contract for Difference) markets. This application analyzes market data in near real-time, generates long/short signals with precise entry, stop-loss, and take-profit levels, filters macro events, and sends alerts via Telegram, Slack, or email.

## ⚠️ WARNING

**This is not investment advice. CFD trading involves high risk and can result in significant losses. Past performance does not guarantee future results. Use this software at your own risk.**

## Features

### Core Functionality
- **Multi-timeframe Analysis**: HTF (Higher Timeframe) for trend, LTF (Lower Timeframe) for entries
- **Technical Indicators**: SMA, EMA, MACD, RSI, ATR, Donchian Channels, Bollinger Bands, ROC
- **Signal Generation**: Automated LONG/SHORT signals with precise entry, SL, and TP levels
- **Risk Management**: Position sizing, daily loss limits, maximum open signals
- **Macro Event Filtering**: Avoids trading during high-impact economic events
- **Multi-channel Alerts**: Telegram, Slack, and email notifications

### Data Providers
- **Yahoo Finance**: Intraday and EOD data (with delays)
- **Stooq**: Free EOD data
- **Broker WebSocket**: Template for real-time broker integration

### Dashboard & Analytics
- **Streamlit Dashboard**: Real-time monitoring, signal history, performance metrics
- **Backtesting**: Historical performance analysis with detailed reports
- **Performance Metrics**: CAGR, Max Drawdown, Sharpe Ratio, Win Rate, Profit Factor

## Installation

### Prerequisites
- Python 3.11+
- Docker (optional)
- Telegram Bot Token (for alerts)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cfd_trader_assistant
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Configure trading parameters**
   - Edit `config/instruments.yaml` - Add your trading instruments
   - Edit `config/rules.yaml` - Adjust trading rules and risk parameters
   - Edit `config/account.yaml` - Set account settings and alert configurations
   - Edit `config/macro.yaml` - Configure macro event calendar

### Docker Installation

1. **Clone and configure**
   ```bash
   git clone <repository-url>
   cd cfd_trader_assistant
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

## Configuration

### Environment Variables (.env)
```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Account Settings
ACCOUNT_EQUITY=10000
RISK_PER_TRADE_PCT=0.008
MAX_DAILY_LOSS_PCT=0.02
```

### Trading Rules (config/rules.yaml)
```yaml
trend:
  sma_long: 200
  sma_mid: 50
  sma_fast: 20

entry:
  donchian_period: 20
  roc_lookback: 10
  roc_min_long: 0.003
  roc_max_short: -0.003

risk:
  stop_atr_mult: 1.5
  rr_ratio: 2.0
  max_open_signals: 5
  risk_per_trade_pct: 0.008
```

### Instruments (config/instruments.yaml)
```yaml
instruments:
  - symbol: "NAS100"
    provider: "YahooProvider"
    yahoo_symbol: "^NDX"
    kind: "index"
    point_value: 1.0
    ltf_interval: "5m"
    htf_interval: "1h"
```

## Usage

### Command Line Interface

#### Market Scanning
```bash
# Intraday scanning (every 5 minutes)
python main.py scan --mode=intraday

# End-of-day scanning
python main.py scan --mode=eod
```

#### Backtesting
```bash
# Run predefined backtests
python main.py backtest --preset=eod_spy_qqq
python main.py backtest --preset=intraday_nas100
python main.py backtest --preset=fx_major_pairs
```

#### Dashboard
```bash
# Start web dashboard
python main.py dashboard --port=8501 --host=0.0.0.0
```

#### System Status
```bash
# Check system status
python main.py status

# Run system tests
python main.py test
```

### Docker Commands

#### Start Services
```bash
# Start all services
docker-compose up -d

# Start only dashboard
docker-compose up -d dashboard

# Start only scanner
docker-compose up -d scanner
```

#### Run Backtests
```bash
# Run backtest
docker-compose run --rm backtest

# Run specific backtest
docker-compose run --rm backtest python main.py backtest --preset=eod_spy_qqq
```

#### View Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f scanner
docker-compose logs -f dashboard
```

## Trading Logic

### Signal Generation Process

1. **Trend Filter (HTF)**
   - LONG: `close > SMA200` AND `SMA20 > SMA50`
   - SHORT: `close < SMA200` AND `SMA20 < SMA50`

2. **Entry Triggers (LTF)**
   - Donchian Breakout: `high > donchian_high(20)` (LONG) or `low < donchian_low(20)` (SHORT)
   - MACD Crossover: Pro-trend MACD signal
   - ROC Momentum: `ROC(10) >= 0.3%` (LONG) or `ROC(10) <= -0.3%` (SHORT)

3. **Quality Filters**
   - Volume: `current_volume >= 1.2 × avg_volume(20)`
   - Volatility: `ATR(14)/close` between 0.3% and 3.0%

4. **Risk Management**
   - Stop Loss: `entry ± 1.5 × ATR(14)`
   - Take Profit: `entry ± 2.0 × (entry - stop_loss)`
   - Position Size: Based on risk per trade (0.8% default)

### Alert Format
```
🚀 New LONG Signal

LONG NAS100 @ 18500.0000
SL: 18450.0000  TP: 18600.0000   RR: 2.0
Risk: $80.00 (0.8% kapitału)  Size: 1.00
Trend(HTF) OK; Breakout(20); ATR 0.8%; Vol 1.3×; brak makro w 30m
```

## Dashboard

Access the dashboard at `http://localhost:8501` to:

- **Signals Tab**: View active signals, filter by symbol/side/status
- **Charts Tab**: Technical analysis with indicators and price charts
- **Performance Tab**: Backtest results, equity curve, performance metrics
- **Settings Tab**: View current configuration (read-only)

## Backtesting

### Available Presets
- `eod_spy_qqq`: 4-year EOD backtest on SPY and QQQ
- `intraday_nas100`: 1-year intraday backtest on NAS100
- `fx_major_pairs`: 2-year EOD backtest on EUR/USD and GBP/USD

### Reports
Backtests generate:
- HTML report with performance metrics
- CSV file with all trades
- Equity curve visualization

## Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_indicators.py

# Run with coverage
pytest --cov=app tests/
```

## Architecture

### Project Structure
```
cfd_trader_assistant/
├── app/
│   ├── providers/          # Data providers
│   ├── indicators.py       # Technical indicators
│   ├── macro.py           # Macro event filtering
│   ├── rules.py           # Trading rules and signals
│   ├── sizing.py          # Position sizing and risk
│   ├── alerts.py          # Alert system
│   ├── dashboard.py       # Streamlit dashboard
│   ├── backtest.py        # Backtesting engine
│   ├── scheduler.py       # Task scheduling
│   └── utils.py           # Utilities
├── config/                # Configuration files
├── data/                  # Data storage
├── tests/                 # Unit tests
├── main.py               # CLI entry point
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker services
└── README.md           # This file
```

### Key Components

1. **Data Providers**: Abstract interface for market data
2. **Indicators**: Technical analysis calculations
3. **Rules Engine**: Signal generation logic
4. **Risk Manager**: Position sizing and risk control
5. **Alert System**: Multi-channel notifications
6. **Scheduler**: Automated scanning and signal generation
7. **Dashboard**: Web-based monitoring interface
8. **Backtester**: Historical performance analysis

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This software is for educational and research purposes only. It is not intended as investment advice. Trading CFDs involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always do your own research and consider consulting with a financial advisor before making investment decisions.

## Support

For issues and questions:
1. Check the documentation
2. Run system tests: `python main.py test`
3. Check logs in the `logs/` directory
4. Open an issue on GitHub

## Roadmap

- [ ] Machine learning signal filters
- [ ] Additional technical indicators
- [ ] More data providers
- [ ] Advanced risk management features
- [ ] Portfolio optimization
- [ ] Real-time broker integration
- [ ] Mobile app
- [ ] API for external integrations