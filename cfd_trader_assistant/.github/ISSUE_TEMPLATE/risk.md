---
name: Risk Management Issue
about: Report problems with risk management or position sizing
title: '[RISK] '
labels: risk-management
assignees: ''
---

**What risk management issue are you experiencing?**
A clear and concise description of the risk management problem.

**Type of issue:**
- [ ] Position sizing problems
- [ ] Risk calculation errors
- [ ] Daily loss limits not working
- [ ] Correlation limits issues
- [ ] Margin calculation problems
- [ ] Risk metrics incorrect
- [ ] Other (please describe)

**Risk component:**
- [ ] Position sizing
- [ ] Stop loss calculation
- [ ] Take profit calculation
- [ ] Daily loss limits
- [ ] Maximum open signals
- [ ] Correlation limits
- [ ] All components

**Symbols affected:**
- [ ] All symbols
- [ ] Specific symbols: [e.g. EURUSD, NAS100, SPY]
- [ ] FX pairs
- [ ] Indices
- [ ] Commodities

**Configuration:**
Please share relevant configuration (remove sensitive information):
```yaml
# config/rules.yaml (risk sections)
```

**Account information:**
- Account equity: [e.g. $10,000]
- Risk per trade: [e.g. 0.8%]
- Maximum daily loss: [e.g. 2.0%]
- Maximum open signals: [e.g. 5]

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Steps to reproduce:**
1. Set up risk management configuration
2. Generate signal for '...'
3. See issue

**Signal information:**
- Signal side: [e.g. LONG, SHORT]
- Entry price: [e.g. 1.1000]
- Stop loss: [e.g. 1.0950]
- Take profit: [e.g. 1.1100]
- Calculated position size: [e.g. 1.0 lots]
- Calculated risk: [e.g. $80]

**Error message:**
```
Paste the complete error message here
```

**Environment:**
 - OS: [e.g. Ubuntu 20.04, Windows 10, macOS 12]
 - Python version: [e.g. 3.11.0]
 - CFD Trader Assistant version: [e.g. 2.0.0]

**What you tried:**
- [ ] Verified risk configuration
- [ ] Tested with different account sizes
- [ ] Tested with different risk percentages
- [ ] Checked position sizing calculations
- [ ] Reviewed risk management rules
- [ ] Other (please describe)

**Additional context**
Add any other context about the risk management issue here.

**Checklist**
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have checked the documentation
- [ ] I have provided configuration (without sensitive data)
- [ ] I have included the error message
- [ ] I have described what I tried
- [ ] I have included system information