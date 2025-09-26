---
name: Data Issue
about: Report problems with data providers or data quality
title: '[DATA] '
labels: data
assignees: ''
---

**What data issue are you experiencing?**
A clear and concise description of the data problem.

**Type of issue:**
- [ ] Data not loading
- [ ] Incorrect data values
- [ ] Missing data
- [ ] Data format issues
- [ ] Provider connection problems
- [ ] Data quality issues
- [ ] Other (please describe)

**Data provider:**
- [ ] Yahoo Finance
- [ ] Stooq
- [ ] Broker WebSocket
- [ ] CSV file
- [ ] Multiple providers

**Data type:**
- [ ] OHLCV data
- [ ] Real-time data
- [ ] Historical data
- [ ] EOD data
- [ ] Intraday data

**Symbols affected:**
- [ ] All symbols
- [ ] Specific symbols: [e.g. EURUSD, NAS100, SPY]
- [ ] FX pairs
- [ ] Indices
- [ ] Commodities

**Timeframe:**
- [ ] 1 minute
- [ ] 5 minutes
- [ ] 15 minutes
- [ ] 1 hour
- [ ] 1 day
- [ ] Multiple timeframes

**Error message:**
```
Paste the complete error message here
```

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Steps to reproduce:**
1. Set up data provider configuration
2. Request data for '...'
3. See issue

**Configuration:**
Please share relevant configuration (remove sensitive information):
```yaml
# config/instruments.yaml (relevant sections)
```

**Data sample:**
If you have a sample of the problematic data, please share it:
```csv
# Paste a sample of the data here
```

**Environment:**
 - OS: [e.g. Ubuntu 20.04, Windows 10, macOS 12]
 - Python version: [e.g. 3.11.0]
 - CFD Trader Assistant version: [e.g. 2.0.0]
 - Network: [e.g. Internet connection, firewall settings]

**What you tried:**
- [ ] Verified data provider configuration
- [ ] Tested data provider manually
- [ ] Checked network connectivity
- [ ] Tried different symbols
- [ ] Tried different timeframes
- [ ] Other (please describe)

**Additional context**
Add any other context about the data issue here.

**Checklist**
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have checked the documentation
- [ ] I have provided configuration (without sensitive data)
- [ ] I have included the error message
- [ ] I have described what I tried
- [ ] I have included system information