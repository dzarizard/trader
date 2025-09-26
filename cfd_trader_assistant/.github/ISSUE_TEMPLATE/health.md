---
name: Health Monitoring Issue
about: Report problems with health monitoring or system status
title: '[HEALTH] '
labels: health-monitoring
assignees: ''
---

**What health monitoring issue are you experiencing?**
A clear and concise description of the health monitoring problem.

**Type of issue:**
- [ ] Health checks failing
- [ ] Circuit breaker issues
- [ ] Retry logic problems
- [ ] System status incorrect
- [ ] Performance monitoring issues
- [ ] Health endpoint problems
- [ ] Other (please describe)

**Health component:**
- [ ] Database connection
- [ ] Data provider health
- [ ] Telegram connection
- [ ] Disk space monitoring
- [ ] Memory usage monitoring
- [ ] All components

**Error message:**
```
Paste the complete error message here
```

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
What actually happened.

**Steps to reproduce:**
1. Run health check command '...'
2. See issue

**Command used:**
```bash
# Paste the command you used
python main.py health --format=json
```

**Health check output:**
```json
# Paste the health check output here
```

**Environment:**
 - OS: [e.g. Ubuntu 20.04, Windows 10, macOS 12]
 - Python version: [e.g. 3.11.0]
 - CFD Trader Assistant version: [e.g. 2.0.0]
 - Available memory: [e.g. 8GB]
 - Available disk space: [e.g. 50GB]

**System resources:**
- CPU usage: [e.g. 25%]
- Memory usage: [e.g. 2GB / 8GB]
- Disk usage: [e.g. 20GB / 100GB]
- Network connectivity: [e.g. Good, Poor, None]

**What you tried:**
- [ ] Verified system resources
- [ ] Checked network connectivity
- [ ] Restarted the application
- [ ] Checked logs
- [ ] Tested individual components
- [ ] Other (please describe)

**Additional context**
Add any other context about the health monitoring issue here.

**Checklist**
- [ ] I have searched existing issues to avoid duplicates
- [ ] I have checked the documentation
- [ ] I have provided the command used
- [ ] I have included the error message
- [ ] I have described what I tried
- [ ] I have included system information