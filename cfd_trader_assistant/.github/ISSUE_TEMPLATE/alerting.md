---
name: Alerting Issue
about: Report problems with alerting functionality
title: '[ALERTS] '
labels: alerting
assignees: ''
---

**What alerting issue are you experiencing?**
A clear and concise description of the alerting problem.

**Type of issue:**
- [ ] Alerts not being sent
- [ ] Incorrect alert content
- [ ] Missing alerts
- [ ] Duplicate alerts
- [ ] Alert formatting issues
- [ ] Channel-specific problems
- [ ] Other (please describe)

**Alert channel:**
- [ ] Telegram
- [ ] Slack
- [ ] Email
- [ ] Multiple channels
- [ ] All channels

**Alert type:**
- [ ] Signal entry alerts
- [ ] Signal exit alerts
- [ ] System alerts
- [ ] Error alerts
- [ ] All alert types

**Configuration:**
Please share relevant configuration (remove sensitive information):
```yaml
# config/account.yaml (alert sections)
```

**Environment variables:**
```bash
# Share relevant environment variables (remove sensitive data)
TELEGRAM_BOT_TOKEN=***
TELEGRAM_CHAT_ID=***
```

**Error message:**
```
Paste the complete error message here
```

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Steps to reproduce:**
1. Set up alerting configuration
2. Generate a signal
3. See issue

**Test scenario:**
- [ ] Manual signal generation
- [ ] Automated scanning
- [ ] Backtesting
- [ ] Dashboard alerts

**Environment:**
 - OS: [e.g. Ubuntu 20.04, Windows 10, macOS 12]
 - Python version: [e.g. 3.11.0]
 - CFD Trader Assistant version: [e.g. 2.0.0]
 - Network: [e.g. Internet connection, firewall settings]

**What you tried:**
- [ ] Verified bot tokens and credentials
- [ ] Tested alert channels manually
- [ ] Checked network connectivity
- [ ] Reviewed configuration
- [ ] Checked logs
- [ ] Other (please describe)

**Additional context**
Add any other context about the alerting issue here.

**Checklist**
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have checked the documentation
- [ ] I have provided configuration (without sensitive data)
- [ ] I have included the error message
- [ ] I have described what I tried
- [ ] I have included system information