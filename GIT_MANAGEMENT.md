# Git Repository Management Guide

This guide explains which files should be committed to the repository and which should be ignored for proper development workflow.

## 📁 Files to Commit to Repository

### ✅ **Documentation Files** (Always commit)
```
DEVELOPMENT_SETUP.md          # Development environment guide
DEPLOYMENT_WORKFLOW.md        # Deployment procedures
MIGRATION_PLAN.md             # Migration instructions
CI_CD_GUIDE.md               # Existing CI/CD documentation
TESTING.md                    # Existing testing guide
README.md                     # Project overview
SECURITY.md                   # Security information
LICENSE                       # License file
```

### ✅ **Configuration Templates** (Always commit)
```
env.example                   # Production environment template
env.dev.example               # Development environment template
docker-compose.yml            # Production Docker Compose
docker-compose.dev.yml        # Development Docker Compose
Dockerfile                    # Docker build instructions
pytest.ini                    # Test configuration
requirements.in               # Python dependencies source
requirements.txt              # Python dependencies locked
requirements-dev.in           # Development dependencies source
requirements-dev.txt          # Development dependencies locked
```

### ✅ **Source Code** (Always commit)
```
src/                         # All source code
tests/                       # All test files
scripts/                     # All scripts (including dev-setup.py)
.github/                     # GitHub Actions workflows
unraid/                      # Unraid container configuration
images/                      # Project images/logos
```

### ✅ **Project Files** (Always commit)
```
.gitignore                   # Git ignore rules
.gitattributes               # Git attributes (if exists)
pyproject.toml               # Python project configuration (if exists)
setup.py                     # Python setup (if exists)
```

## 🚫 Files to Add to .gitignore

### ❌ **Environment Files** (Never commit)
```
.env                         # Production environment (contains secrets)
.env.local                   # Local environment overrides
.env.prod                    # Production environment file
.env.staging                 # Staging environment file
.env.dev                     # Development environment file
```

### ❌ **Development Data** (Never commit)
```
dev-data/                    # Development data directory
dev-data/*                   # All development data files
```

### ❌ **IDE and Editor Files** (Never commit)
```
.vscode/settings.json        # VS Code user settings
.vscode/launch.json          # VS Code debug configurations
.idea/                       # IntelliJ/PyCharm settings
*.swp                        # Vim swap files
*.swo                        # Vim swap files
```

### ❌ **OS and System Files** (Never commit)
```
.DS_Store                    # macOS system files
Thumbs.db                    # Windows thumbnail cache
desktop.ini                  # Windows folder settings
```

### ❌ **Build and Cache Files** (Never commit)
```
__pycache__/                 # Python cache
*.pyc                        # Python compiled files
*.pyo                        # Python optimized files
.pytest_cache/               # Pytest cache
.mypy_cache/                 # MyPy cache
.coverage                    # Coverage data
htmlcov/                     # Coverage HTML reports
```

### ❌ **Logs and Temporary Files** (Never commit)
```
*.log                        # Log files
logs/                        # Log directories
tmp/                         # Temporary files
temp/                        # Temporary files
```

## 🔧 Updated .gitignore

Here's the complete updated `.gitignore` file:

```gitignore
# --- Python / build ---
__pycache__/
*.py[cod]
*.pyo
*.pyd
*.so
*.egg-info/
.build/
dist/
build/

# --- Environment files ---
.env
.env.*
.envrc
.env.local
.env.prod
.env.staging
.env.dev

# --- Development data ---
dev-data/
dev-data/*

# --- Tools / editors ---
.pytest_cache/
.mypy_cache/
coverage.*
htmlcov/
.cache/
.idea/
.vscode/settings.json
.vscode/launch.json
*.swp
*.swo

# --- OS noise ---
.DS_Store
Thumbs.db
desktop.ini

# --- App data (keep folder, ignore contents) ---
data/*
!data/.gitkeep

# --- Logs ---
logs/
*.log

# --- Temporary files ---
tmp/
temp/

# --- Production data (if any) ---
/src/manganotify/data/watchlist.json
/src/manganotify/data/notifications.json
```

## 📋 File Management Best Practices

### **Environment Files**
- ✅ **Commit**: `env.example`, `env.dev.example` (templates)
- ❌ **Ignore**: `.env`, `.env.dev`, `.env.prod` (actual configs with secrets)

### **Docker Files**
- ✅ **Commit**: `docker-compose.yml`, `docker-compose.dev.yml`, `Dockerfile`
- ❌ **Ignore**: Any local Docker override files

### **Development Files**
- ✅ **Commit**: `scripts/dev-setup.py`, `docker-compose.dev.yml`
- ❌ **Ignore**: `dev-data/`, `.env.dev` (actual dev environment)

### **Documentation**
- ✅ **Commit**: All `.md` files (guides, documentation)
- ❌ **Ignore**: Personal notes, TODO files

## 🚀 Quick Setup Commands

### **Initial Repository Setup**
```bash
# Add all the new files
git add DEVELOPMENT_SETUP.md
git add DEPLOYMENT_WORKFLOW.md
git add MIGRATION_PLAN.md
git add env.dev.example
git add docker-compose.dev.yml
git add scripts/dev-setup.py

# Update .gitignore
git add .gitignore

# Commit the changes
git commit -m "Add development environment setup and documentation"
```

### **After Migration (Local Development)**
```bash
# Create local development environment
cp env.dev.example .env.dev
# Edit .env.dev with your settings

# Create development data directory
mkdir dev-data

# These files will be ignored by git automatically
```

## 🔍 Verification Commands

### **Check What Will Be Committed**
```bash
# See what files are staged
git status

# See what files are ignored
git status --ignored

# Check if sensitive files are being tracked
git ls-files | grep -E "\.(env|key|secret)"
```

### **Verify .gitignore is Working**
```bash
# Try to add an ignored file (should show as ignored)
git add .env.dev
git status

# Check if development data is ignored
git add dev-data/
git status
```

## 🚨 Security Considerations

### **Never Commit These**
- 🔒 **API keys** and tokens
- 🔒 **Database passwords**
- 🔒 **Authentication secrets**
- 🔒 **Personal configuration**
- 🔒 **Production data**

### **Safe to Commit**
- ✅ **Configuration templates** (with placeholder values)
- ✅ **Documentation** and guides
- ✅ **Source code** and tests
- ✅ **Docker configurations**
- ✅ **Scripts** and automation

## 📚 File Purpose Summary

| File | Purpose | Commit? | Reason |
|------|---------|---------|---------|
| `DEVELOPMENT_SETUP.md` | Development guide | ✅ | Documentation |
| `DEPLOYMENT_WORKFLOW.md` | Deployment procedures | ✅ | Documentation |
| `MIGRATION_PLAN.md` | Migration instructions | ✅ | Documentation |
| `env.dev.example` | Dev config template | ✅ | Template for others |
| `docker-compose.dev.yml` | Dev Docker setup | ✅ | Development configuration |
| `scripts/dev-setup.py` | Setup automation | ✅ | Development tool |
| `.env.dev` | Your dev config | ❌ | Contains your personal settings |
| `dev-data/` | Development data | ❌ | Local data, not needed by others |

## 🎯 Next Steps

1. **Update `.gitignore`** with the new rules
2. **Commit the new files** to the repository
3. **Test the setup** locally
4. **Verify sensitive files** are not tracked
5. **Document any customizations** you make

This setup ensures that:
- ✅ **Documentation** is shared with the team
- ✅ **Templates** help others set up their environment
- ✅ **Secrets** are never accidentally committed
- ✅ **Development data** stays local
- ✅ **Repository** stays clean and professional
