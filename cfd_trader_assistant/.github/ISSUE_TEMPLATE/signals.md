---
name: Signal Issue
about: Report problems with signal generation or quality
title: '[SIGNALS] '
labels: signals
assignees: ''
---

**What signal issue are you experiencing?**
A clear and concise description of the signal problem.

**Type of issue:**
- [ ] No signals generated
- [ ] Incorrect signal direction
- [ ] Wrong entry/exit levels
- [ ] Signal quality issues
- [ ] Signal timing problems
- [ ] Signal filtering issues
- [ ] Other (please describe)

**Signal type:**
- [ ] LONG signals
- [ ] SHORT signals
- [ ] Both LONG and SHORT
- [ ] Exit signals
- [ ] All signal types

**Symbols affected:**
- [ ] All symbols
- [ ] Specific symbols: [e.g. EURUSD, NAS100, SPY]
- [ ] FX pairs
- [ ] Indices
- [ ] Commodities

**Timeframe:**
- [ ] Intraday (5m, 15m)
- [ ] EOD (1d)
- [ ] Multiple timeframes
- [ ] All timeframes

**Configuration:**
Please share relevant configuration (remove sensitive information):
```yaml
# config/rules.yaml (relevant sections)
```

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Steps to reproduce:**
1. Set up signal configuration
2. Run scanning for '...'
3. See issue

**Market conditions:**
- Market trend: [e.g. Bullish, Bearish, Sideways]
- Volatility: [e.g. High, Medium, Low]
- Time of day: [e.g. Market open, Market close, After hours]
- Economic events: [e.g. None, CPI release, FOMC meeting]

**Data information:**
- Data source: [e.g. Yahoo Finance, Stooq, CSV file]
- Data quality: [e.g. Good, Missing bars, Gaps]
- Time period: [e.g. Last 30 days, Last 6 months]

**Error message:**
```
Paste the complete error message here
```

**Environment:**
 - OS: [e.g. Ubuntu 20.04, Windows 10, macOS 12]
 - Python version: [e.g. 3.11.0]
 - CFD Trader Assistant version: [e.g. 2.0.0]

**What you tried:**
- [ ] Verified signal configuration
- [ ] Tested with different symbols
- [ ] Tested with different timeframes
- [ ] Checked data quality
- [ ] Reviewed signal rules
- [ ] Other (please describe)

**Additional context**
Add any other context about the signal issue here.

**Checklist**
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have checked the documentation
- [ ] I have provided configuration (without sensitive data)
- [ ] I have included the error message
- [ ] I have described what I tried
- [ ] I have included system information