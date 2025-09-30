# Testing Guide for MangaNotify

This document explains how to run tests for MangaNotify to ensure reliability and catch issues like missed notifications before deployment.

## Overview

MangaNotify has a comprehensive test suite that covers:

- **Unit Tests**: Individual components and functions
- **Integration Tests**: End-to-end API functionality
- **Poller Tests**: Core notification detection logic
- **Configuration Tests**: Environment and settings validation
- **Security Tests**: Vulnerability scanning

## Quick Start

### Run All Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/manganotify --cov-report=html
```

### Run Specific Test Categories
```bash
# Test the poller functionality (catches notification issues)
pytest tests/test_poller.py -v

# Test API endpoints
pytest tests/test_api_endpoints.py -v

# Test configuration
pytest tests/test_config.py -v

# Test integration scenarios
pytest tests/test_integration.py -v
```

## Test Categories

### 1. Poller Tests (`test_poller.py`)

These tests specifically address missed notification issues:

- **Notification Detection**: Tests that new chapters are detected
- **API Failure Handling**: Tests graceful handling of API outages
- **Retry Logic**: Tests automatic retry on temporary failures
- **Notification Preferences**: Tests filtering based on user settings
- **Real-world Scenarios**: Tests specific missed update scenarios

**Key Test**: `test_missed_update_scenario`
This test reproduces the exact conditions that caused a missed notification.

### 2. API Endpoint Tests (`test_api_endpoints.py`)

Tests all API endpoints including:

- **Watchlist Management**: Add, remove, update series
- **Import/Export**: Watchlist data transfer
- **Progress Tracking**: Reading progress updates
- **Notifications**: Notification history and management
- **Health Checks**: System status endpoints

### 3. Configuration Tests (`test_config.py`)

Tests configuration handling:

- **Environment Variables**: Proper loading and validation
- **Default Values**: Correct fallbacks
- **Validation**: Invalid values are handled gracefully
- **Isolation**: Tests don't interfere with each other

### 4. Integration Tests (`test_integration.py`)

End-to-end testing:

- **Authentication Flow**: Login, logout, token validation
- **CORS Handling**: Cross-origin requests
- **Error Handling**: Malformed requests
- **Token Expiration**: Security features

## Running Tests Before Deployment

### 1. Pre-commit Hooks

Install pre-commit hooks to run tests automatically:

```bash
pip install pre-commit
pre-commit install
```

This will run tests, linting, and security checks before each commit.

### 2. Manual Testing

Before deploying a new container:

```bash
# Run the comprehensive test suite
python scripts/run_tests.py

# Or run specific tests
python scripts/run_tests.py --poller --api --coverage
```

### 3. Docker Testing

Test the Docker container:

```bash
# Build and test the container
docker build -t manganotify-test .
docker run --rm -p 8999:8999 \
  -e POLL_INTERVAL_SEC=0 \
  -e AUTH_ENABLED=false \
  manganotify-test &

# Test endpoints
curl http://localhost:8999/api/health
curl http://localhost:8999/api/watchlist

# Clean up
docker stop $(docker ps -q --filter ancestor=manganotify-test)
```

## CI/CD Integration

### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/test.yml`) that:

- Runs tests on Python 3.11 and 3.12
- Tests Docker builds
- Performs security scans
- Generates coverage reports

### Local CI Simulation

Simulate the CI environment locally:

```bash
# Run the same tests as CI
pytest tests/ -v --tb=short
pytest tests/ --cov=src/manganotify --cov-report=xml

# Security scan
bandit -r src/
safety check

# Docker test
docker build -t manganotify-test .
docker run --rm manganotify-test python -c "import manganotify; print('OK')"
```

## Test Data and Fixtures

### Temporary Data

Tests use temporary directories and files to avoid conflicts:

- **`temp_data_dir`**: Isolated data directory for each test
- **`sample_watchlist`**: Pre-populated watchlist for testing
- **`sample_notifications`**: Test notification data

### Mocking

Tests use mocks to avoid external dependencies:

- **API Calls**: Mocked manga API responses
- **HTTP Requests**: Simulated network calls
- **File System**: Temporary directories

## Debugging Failed Tests

### Common Issues

1. **Import Errors**: Ensure `src/` is in Python path
2. **Permission Errors**: Check temporary directory permissions
3. **Network Timeouts**: Tests use mocks, no real network calls
4. **Environment Conflicts**: Tests isolate environment variables

### Debug Mode

Run tests with maximum verbosity:

```bash
pytest tests/ -vvv --tb=long --capture=no
```

### Test Specific Scenarios

To test the exact missed update scenario:

```bash
pytest tests/test_poller.py::TestMissedNotificationScenario::test_missed_update_scenario -vvv
```

## Coverage Reports

Generate detailed coverage reports:

```bash
# HTML report (opens in browser)
pytest tests/ --cov=src/manganotify --cov-report=html
open htmlcov/index.html

# Terminal report
pytest tests/ --cov=src/manganotify --cov-report=term-missing

# XML report (for CI)
pytest tests/ --cov=src/manganotify --cov-report=xml
```

## Performance Testing

For performance-critical tests:

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Profile slow tests
pytest tests/ --profile
```

## Security Testing

Regular security scans:

```bash
# Install security tools
pip install bandit safety

# Run security scan
bandit -r src/

# Check for known vulnerabilities
safety check
```

## Best Practices

1. **Run tests before every commit**
2. **Add tests for new features**
3. **Test error conditions, not just happy paths**
4. **Use descriptive test names**
5. **Keep tests isolated and independent**
6. **Mock external dependencies**
7. **Test configuration changes**

## Troubleshooting

### Test Environment Issues

If tests fail due to environment issues:

```bash
# Clean Python cache
find . -name "__pycache__" -delete
find . -name "*.pyc" -delete

# Reinstall dependencies
pip install --force-reinstall -r requirements-dev.txt

# Reset test environment
unset DATA_DIR POLL_INTERVAL_SEC AUTH_ENABLED
```

### Docker Test Issues

If Docker tests fail:

```bash
# Clean Docker
docker system prune -f
docker build --no-cache -t manganotify-test .

# Check container logs
docker logs <container_id>
```

## Contributing

When adding new tests:

1. Follow the existing naming conventions
2. Use appropriate fixtures and mocks
3. Test both success and failure cases
4. Add docstrings explaining test purpose
5. Update this documentation if needed

## Monitoring

In production, monitor:

- **Poller Health**: Check `/api/health/details`
- **Notification Success**: Monitor notification logs
- **API Response Times**: Track manga API performance
- **Error Rates**: Monitor failed requests

The test suite helps ensure these systems work correctly before deployment.
