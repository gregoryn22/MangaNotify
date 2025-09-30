# CI/CD Integration Guide for MangaNotify

This guide explains how the comprehensive test suite integrates with your existing GitHub Actions workflows to prevent issues like missed notifications.

## 🔄 Workflow Overview

Your project now has **5 GitHub Actions workflows** that work together:

### 1. **Pull Request Checks** (`pr-checks.yml`)
**Triggers**: Every pull request
**Purpose**: Quick validation before code review

**What it tests**:
- ✅ Critical poller logic (prevents notification issues)
- ✅ Missed notification scenario test (reproduces the exact failure)
- ✅ Basic API endpoints
- ✅ Docker build and startup
- ✅ Code quality (linting, formatting)
- ✅ Security scan

**Runtime**: ~5-10 minutes

### 2. **Test Suite** (`test.yml`)
**Triggers**: Push to main/master, pull requests
**Purpose**: Comprehensive testing

**What it tests**:
- ✅ Full test suite with coverage
- ✅ Integration tests
- ✅ Docker functionality
- ✅ Security scanning
- ✅ Multiple Python versions (3.11, 3.12)

**Runtime**: ~15-20 minutes

### 3. **Docker Build** (`docker.yml`)
**Triggers**: Push to main/master, tags
**Purpose**: Build and publish Docker images

**What it tests**:
- ✅ Critical tests before building
- ✅ Multi-platform builds (amd64, arm64)
- ✅ Registry publishing

**Runtime**: ~10-15 minutes

### 4. **Docker Publish** (`docker-publish.yml`)
**Triggers**: Push to master branch
**Purpose**: Master branch CI/CD

**What it tests**:
- ✅ Comprehensive test suite
- ✅ Missed notification scenario test
- ✅ Docker publishing to GHCR

**Runtime**: ~15-20 minutes

### 5. **Release Testing** (`release-test.yml`)
**Triggers**: Version tags (v*.*.*), manual dispatch
**Purpose**: Thorough testing before releases

**What it tests**:
- ✅ Full test suite on multiple Python versions
- ✅ Docker release testing
- ✅ Comprehensive security scanning
- ✅ Performance testing
- ✅ Image size validation

**Runtime**: ~20-30 minutes

## 🎯 Key Integration Points

### **Prevents Missed Notification Issues**

Every workflow now includes:
```yaml
- name: Run missed notification scenario test
  run: |
    pytest tests/test_poller.py::TestMissedNotificationScenario -v
```

This test reproduces the exact conditions that caused the missed notification and ensures it won't happen again.

### **Critical Test Prioritization**

**Fast Tests** (PR checks):
- Poller logic tests
- Basic API endpoints
- Configuration validation

**Comprehensive Tests** (main/master):
- Full test suite
- Integration tests
- Security scans

**Release Tests** (tags):
- Multi-version testing
- Performance validation
- Docker optimization

## 🚀 How to Use

### **For Development**

1. **Make changes** to your code
2. **Create a pull request**
3. **PR checks run automatically** (5-10 min)
4. **Review results** before merging
5. **Merge when green** ✅

### **For Releases**

1. **Create a version tag**: `git tag v1.2.3`
2. **Push the tag**: `git push origin v1.2.3`
3. **Release tests run automatically** (20-30 min)
4. **Docker image published** to GHCR
5. **Deploy with confidence** 🚀

### **Manual Testing**

You can trigger release tests manually:
1. Go to **Actions** tab in GitHub
2. Select **Release Testing** workflow
3. Click **Run workflow**
4. Choose test level (quick/full/comprehensive)

## 📊 Test Coverage by Workflow

| Test Category | PR Checks | Test Suite | Docker Build | Release |
|---------------|-----------|------------|--------------|---------|
| Poller Logic | ✅ Critical | ✅ Full | ✅ Critical | ✅ Full |
| API Endpoints | ✅ Basic | ✅ Full | ✅ Critical | ✅ Full |
| Configuration | ✅ Basic | ✅ Full | ✅ Basic | ✅ Full |
| Integration | ❌ | ✅ Full | ❌ | ✅ Full |
| Security | ✅ Basic | ✅ Full | ❌ | ✅ Comprehensive |
| Docker | ✅ Startup | ✅ Full | ✅ Build | ✅ Release |
| Performance | ❌ | ❌ | ❌ | ✅ Full |

## 🔧 Customization

### **Adding New Tests**

1. **Add test file** to `tests/` directory
2. **Update test runner** in `scripts/run_tests.py`
3. **Tests run automatically** in all workflows

### **Modifying Test Levels**

**Quick tests** (PR checks):
```yaml
pytest tests/test_poller.py::TestPollerLogic -v
pytest tests/test_api_endpoints.py::TestWatchlistEndpoints::test_get_watchlist -v
```

**Full tests** (main/master):
```yaml
python scripts/run_tests.py --coverage --verbose
```

**Comprehensive tests** (releases):
```yaml
python scripts/run_tests.py --coverage --verbose
pytest tests/test_poller.py::TestMissedNotificationScenario -v
```

### **Environment Variables**

All workflows use consistent test environment:
```yaml
env:
  PYTHONPATH: ${{ github.workspace }}/src
  MANGABAKA_BASE: "https://api.mangabaka.dev"
  POLL_INTERVAL_SEC: "0"
  AUTH_ENABLED: "false"
  DATA_DIR: "/tmp/test_data"
  PUSHOVER_APP_TOKEN: ""
  PUSHOVER_USER_KEY: ""
```

## 🚨 Failure Handling

### **PR Checks Fail**
- **Don't merge** the PR
- **Fix the issues** locally
- **Push fixes** to trigger new checks
- **Merge when green** ✅

### **Main Branch Tests Fail**
- **Investigate** the failure
- **Check logs** in Actions tab
- **Fix and push** new commit
- **Monitor** until green ✅

### **Release Tests Fail**
- **Don't deploy** the release
- **Fix issues** in code
- **Create new tag** with fixes
- **Re-run** release tests

## 📈 Monitoring

### **GitHub Actions Dashboard**
- View all workflow runs
- Check success/failure rates
- Monitor test durations
- Review security scan results

### **Coverage Reports**
- Generated in `htmlcov/` directory
- Uploaded as artifacts
- Track coverage trends over time

### **Security Reports**
- Bandit scan results
- Safety vulnerability checks
- Semgrep pattern matching
- Uploaded as artifacts for review

## 🎯 Benefits

### **Prevents Production Issues**
- ✅ Catches notification failures before deployment
- ✅ Validates API functionality
- ✅ Ensures Docker builds work correctly
- ✅ Scans for security vulnerabilities

### **Improves Development Workflow**
- ✅ Fast feedback on PRs (5-10 min)
- ✅ Comprehensive testing on main branch
- ✅ Automated Docker publishing
- ✅ Consistent test environment

### **Ensures Release Quality**
- ✅ Multi-version testing
- ✅ Performance validation
- ✅ Security scanning
- ✅ Docker optimization

## 🔍 Troubleshooting

### **Tests Fail Locally But Pass in CI**
- Check environment variables
- Ensure Python path is correct
- Verify test dependencies are installed

### **Docker Tests Fail**
- Check Docker build logs
- Verify environment variables in container
- Test container startup manually

### **Security Scans Fail**
- Review bandit/safety reports
- Fix security issues in code
- Update dependencies if needed

### **Performance Tests Slow**
- Check test database setup
- Optimize test data creation
- Consider test parallelization

## 📚 Next Steps

1. **Monitor** the first few workflow runs
2. **Adjust** test levels based on feedback
3. **Add** additional tests as needed
4. **Optimize** test performance
5. **Document** any customizations

The integrated CI/CD pipeline now ensures that issues like missed notifications are caught before they reach production, giving you confidence in every deployment! 🚀
