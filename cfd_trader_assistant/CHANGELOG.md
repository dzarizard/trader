# Changelog

All notable changes to the CFD Trader Assistant project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-19

### Added
- **Unified Signal Engine** (`app/signal_engine.py`): Single engine for both live and backtest modes
- **Pricing Engine** (`app/pricing.py`): Advanced price rounding and validation utilities
- **Health Monitoring** (`app/health.py`): System health checks, circuit breakers, retry logic
- **Enhanced Risk Management**: Correlation limits, improved position sizing
- **Cost Management**: Spread, commission, and swap cost calculations
- **Macro Event Filtering**: Configurable no-trade windows around economic events
- **Anti Look-ahead Bias**: Proper HTF indicator shifting to prevent future data leakage
- **Health Check Command**: `python main.py health` for system monitoring
- **Makefile**: Development automation with common commands
- **Enhanced Testing**: Comprehensive test suite with edge cases and integration tests

### Changed
- **Data Provider Interface**: Standardized UTC timestamps across all providers
- **Alert System**: Enhanced with detailed signal information and net P&L
- **Dashboard**: Added Macro tab, enhanced performance metrics
- **Backtesting**: Now includes transaction costs and net P&L calculations
- **Configuration**: Added fees model and enhanced macro filter settings
- **Docker**: Added health checks, resource limits, improved configuration
- **Dependencies**: Pinned versions for reproducible builds

### Fixed
- **Look-ahead Bias**: Eliminated by proper HTF indicator shifting
- **Signal Consistency**: Live and backtest now use identical logic
- **Price Rounding**: Proper tick size handling for all instruments
- **Risk Management**: Improved correlation checks and position sizing
- **Error Handling**: Better retry logic and circuit breaker patterns

### Security
- **Environment Variables**: Proper handling of sensitive configuration
- **Input Validation**: Enhanced validation for all user inputs
- **Error Logging**: Improved error handling without exposing sensitive data

## [1.0.0] - 2024-12-01

### Added
- **Initial Release**: Basic CFD trading signal generator
- **Multi-timeframe Analysis**: HTF and LTF signal generation
- **Technical Indicators**: SMA, EMA, MACD, RSI, ATR, Donchian, ROC
- **Risk Management**: Basic position sizing and daily loss limits
- **Alert System**: Telegram, Slack, and email notifications
- **Streamlit Dashboard**: Web interface for monitoring and configuration
- **Backtesting Framework**: Historical performance analysis
- **Data Providers**: Yahoo Finance, Stooq, and broker WebSocket template
- **Scheduler**: Automated market scanning (intraday/EOD)
- **Docker Support**: Containerized deployment
- **Configuration System**: YAML-based configuration management

### Technical Details
- **Python 3.11**: Modern Python with type hints
- **Pydantic**: Data validation and serialization
- **Pandas/NumPy**: Data processing and analysis
- **Plotly**: Interactive charts and visualizations
- **Streamlit**: Web dashboard framework
- **VectorBT**: Backtesting engine
- **Docker**: Containerization and deployment

## [Unreleased]

### Planned Features
- **Machine Learning Integration**: ML-based signal enhancement
- **Advanced Risk Models**: VaR, CVaR, and portfolio optimization
- **Real-time Broker Integration**: Direct order execution (read-only)
- **Advanced Analytics**: More sophisticated performance metrics
- **Multi-asset Support**: Cryptocurrency and commodity trading
- **API Endpoints**: REST API for external integrations
- **Mobile App**: React Native mobile application
- **Cloud Deployment**: AWS/Azure deployment templates

### Known Issues
- Yahoo Finance data may have delays (15-20 minutes)
- Some indicators may not work correctly with very short timeframes
- Memory usage can be high with large backtest datasets
- Telegram rate limiting may occur with high-frequency signals

---

## Migration Guide

### From v1.0.0 to v2.0.0

#### Configuration Changes
1. **Update `config/rules.yaml`**:
   ```yaml
   # Add new fees section
   fees:
     spread: 0.0001
     commission: 0.0001
     swap_rate: 0.0001
   
   # Add correlation limits
   risk:
     max_correlated_positions: 2
   
   # Enhanced macro filters
   filters:
     macro:
       major_event_hours_before: 24
   ```

2. **Update environment variables**:
   ```bash
   # Add health check configuration
   HEALTH_CHECK_INTERVAL=30
   CIRCUIT_BREAKER_THRESHOLD=5
   ```

#### Code Changes
1. **Import new modules**:
   ```python
   from app.signal_engine import SignalEngine
   from app.pricing import PricingEngine, FeesModel
   from app.health import health_monitor
   ```

2. **Update signal generation**:
   ```python
   # Old way
   signal_generator = SignalGenerator(config)
   
   # New way
   signal_engine = SignalEngine(config)
   ```

3. **Update backtesting**:
   ```python
   # Now includes cost calculations automatically
   result = backtest_engine.run_backtest(...)
   print(f"Net P&L: {result.net_pnl}")
   ```

#### Breaking Changes
- Signal generation logic has changed - backtest results may differ
- Alert format has been enhanced with additional fields
- Some configuration options have been renamed or moved
- Health monitoring is now mandatory for production deployments

---

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Support

For support and questions:
- Create an issue on GitHub
- Check the documentation in README.md
- Review the test files for usage examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.