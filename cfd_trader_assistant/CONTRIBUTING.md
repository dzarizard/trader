# Contributing to CFD Trader Assistant

Thank you for your interest in contributing to the CFD Trader Assistant project! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contributing Guidelines](#contributing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)
- [Issue Reporting](#issue-reporting)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/cfd_trader_assistant.git
   cd cfd_trader_assistant
   ```
3. **Set up the development environment** (see below)

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- Docker (optional, for testing)

### Setup Steps

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # If available
   ```

3. **Install development tools**:
   ```bash
   pip install black isort mypy pytest pytest-cov
   ```

4. **Set up pre-commit hooks** (optional):
   ```bash
   pre-commit install
   ```

5. **Copy configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Using Makefile

The project includes a Makefile for common development tasks:

```bash
# Setup development environment
make dev-setup

# Run tests
make test

# Format code
make format

# Run linting
make lint

# Clean temporary files
make clean
```

## Contributing Guidelines

### General Guidelines

1. **Follow PEP 8** style guidelines
2. **Use type hints** for all function parameters and return values
3. **Write docstrings** for all public functions and classes
4. **Keep functions small** and focused on a single responsibility
5. **Use meaningful variable names** and avoid abbreviations
6. **Handle errors gracefully** with proper exception handling

### Code Style

We use the following tools for code formatting and linting:

- **Black**: Code formatting
- **isort**: Import sorting
- **mypy**: Type checking
- **flake8**: Linting

Run these tools before submitting:

```bash
make format  # Format code with black and isort
make lint    # Run mypy and flake8
```

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add health monitoring system
fix: resolve look-ahead bias in signal generation
docs: update README with new features
test: add tests for pricing engine
refactor: simplify signal validation logic
```

### Branch Naming

Use descriptive branch names:

- `feature/health-monitoring`
- `fix/signal-consistency`
- `docs/api-documentation`
- `test/pricing-engine`

## Pull Request Process

1. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the guidelines above

3. **Write tests** for your changes (see Testing section)

4. **Update documentation** if needed

5. **Run tests** to ensure everything works:
   ```bash
   make test
   ```

6. **Commit your changes** with clear messages

7. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

8. **Create a Pull Request** on GitHub with:
   - Clear title and description
   - Reference to any related issues
   - Screenshots (if UI changes)
   - Test results

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_signal_engine.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_signal_engine.py::TestSignalEngine::test_check_trend_filter -v
```

### Writing Tests

1. **Test files** should be in the `tests/` directory
2. **Test classes** should start with `Test`
3. **Test methods** should start with `test_`
4. **Use descriptive names** for test methods
5. **Test both success and failure cases**
6. **Use fixtures** for common setup code

Example test:

```python
def test_signal_generation_with_valid_data(self):
    """Test signal generation with valid market data."""
    # Arrange
    htf_data = self.create_sample_data(periods=300)
    ltf_data = self.create_sample_data(periods=1000)
    
    # Act
    signals = self.signal_engine.generate_signals(
        htf_data, ltf_data, 'EURUSD', self.instrument_config
    )
    
    # Assert
    assert len(signals) >= 0
    for signal in signals:
        assert signal.side in ['LONG', 'SHORT']
        assert signal.entry_price > 0
```

### Test Categories

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Test with large datasets

## Documentation

### Code Documentation

- **Docstrings**: Use Google style docstrings
- **Type Hints**: Include for all public APIs
- **Comments**: Explain complex logic, not obvious code

Example:

```python
def calculate_position_size(
    self,
    signal: Signal,
    instrument: Instrument,
    current_price: float = None
) -> PositionPlan:
    """
    Calculate optimal position size for a signal with costs.
    
    Args:
        signal: Trading signal with entry, SL, and TP levels
        instrument: Instrument configuration with risk parameters
        current_price: Current market price (if different from entry)
        
    Returns:
        PositionPlan with sizing details including costs
        
    Raises:
        ValueError: If position size cannot be calculated
    """
```

### API Documentation

- **README.md**: Main project documentation
- **CHANGELOG.md**: Version history and changes
- **CONTRIBUTING.md**: This file
- **Code comments**: Inline documentation

### Updating Documentation

When making changes:

1. **Update docstrings** for modified functions
2. **Update README.md** if adding new features
3. **Update CHANGELOG.md** for significant changes
4. **Add examples** for new functionality

## Issue Reporting

### Before Creating an Issue

1. **Search existing issues** to avoid duplicates
2. **Check documentation** for solutions
3. **Try latest version** to see if issue is fixed

### Creating an Issue

Use the issue template and include:

- **Clear title** describing the problem
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, etc.)
- **Error messages** and logs
- **Screenshots** if applicable

### Issue Labels

- `bug`: Something isn't working
- `enhancement`: New feature or request
- `documentation`: Improvements to documentation
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed

## Development Workflow

### Daily Development

1. **Start with latest main**:
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make changes** and test frequently

4. **Commit often** with clear messages

5. **Push regularly** to backup work

### Code Review Process

1. **Self-review** your code before submitting
2. **Address feedback** promptly and professionally
3. **Keep PRs focused** on a single feature/fix
4. **Respond to comments** and questions

### Release Process

1. **Update version** in relevant files
2. **Update CHANGELOG.md** with changes
3. **Create release notes**
4. **Tag release** in Git
5. **Deploy** to production

## Getting Help

- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For questions and general discussion
- **Documentation**: Check README.md and code comments
- **Tests**: Look at test files for usage examples

## Recognition

Contributors will be recognized in:
- **CONTRIBUTORS.md** file
- **Release notes** for significant contributions
- **GitHub contributors** page

Thank you for contributing to CFD Trader Assistant! 🚀