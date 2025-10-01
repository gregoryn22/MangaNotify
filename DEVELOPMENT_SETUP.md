# Development Setup Guide for MangaNotify

This guide helps you set up an optimal development environment that separates development from production, making your workflow safer and more efficient.

## 🎯 Recommended Setup: Local Development + Remote Production

### Why This Approach?

**Current Issues:**
- Development and production mixed in same location
- Risk of accidentally affecting production
- Slower development cycle due to network latency
- Harder to experiment safely

**Benefits of Local Development:**
- ✅ **Faster iteration** - No network delays
- ✅ **Safer experimentation** - Can't break production
- ✅ **Better debugging** - Full IDE integration
- ✅ **Consistent environment** - Same Docker setup everywhere
- ✅ **Easier testing** - Run tests locally before deployment

## 🚀 Setup Instructions

### Step 1: Move Workspace to Windows Machine

1. **Create local development directory:**
   ```bash
   mkdir C:\dev\MangaNotify
   cd C:\dev\MangaNotify
   ```

2. **Clone your repository:**
   ```bash
   git clone https://github.com/gregoryn22/MangaNotify.git .
   ```

3. **Install Docker Desktop** (if not already installed):
   - Download from [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Ensure WSL2 backend is enabled

### Step 2: Create Development Environment

1. **Create development environment file:**
   ```bash
   cp env.example .env.dev
   ```

2. **Configure development settings in `.env.dev`:**
   ```env
   # Development Configuration
   MANGABAKA_BASE=https://api.mangabaka.dev
   PORT=8999
   DATA_DIR=./dev-data
   POLL_INTERVAL_SEC=0  # Disable polling in dev
   
   # CORS - Allow local development
   CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080
   
   # Authentication - Disabled for easier development
   AUTH_ENABLED=false
   
   # Logging - More verbose for development
   LOG_LEVEL=DEBUG
   LOG_FORMAT=plain
   
   # Development flags
   PYTHONDONTWRITEBYTECODE=1
   ```

3. **Create development Docker Compose file:**
   ```bash
   cp docker-compose.yml docker-compose.dev.yml
   ```

4. **Modify `docker-compose.dev.yml` for development:**
   ```yaml
   services:
     manganotify-dev:
       build: .
       container_name: manganotify-dev
       ports:
         - "8999:8999"
       env_file:
         - .env.dev
       volumes:
         # Mount source code for live reloading
         - ./src:/app/src
         - ./dev-data:/data
         # Mount static files for live editing
         - ./src/manganotify/static:/app/src/manganotify/static
       environment:
         - PYTHONPATH=/app/src
         - DATA_DIR=/data
       # Remove restart policy for development
       # restart: unless-stopped
       command: ["uvicorn", "manganotify.main:app", "--host", "0.0.0.0", "--port", "8999", "--reload"]
   ```

### Step 3: Development Workflow

#### Daily Development Commands

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Run tests
python scripts/run_tests.py

# Run specific test categories
python scripts/run_tests.py --poller --coverage

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

#### Testing Before Deployment

```bash
# Run full test suite
python scripts/run_tests.py --coverage --verbose

# Test Docker build
docker build -t manganotify-test .

# Test production-like environment
docker run --rm -p 8999:8999 \
  -e POLL_INTERVAL_SEC=0 \
  -e AUTH_ENABLED=false \
  -e DATA_DIR=/data \
  manganotify-test
```

### Step 4: Production Deployment

#### Option A: Automated Deployment (Recommended)

1. **Push changes to GitHub:**
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

2. **GitHub Actions automatically:**
   - Runs tests
   - Builds Docker image
   - Publishes to GHCR
   - Updates Unraid container

#### Option B: Manual Deployment

1. **Build production image:**
   ```bash
   docker build -t manganotify-prod .
   ```

2. **Tag and push to registry:**
   ```bash
   docker tag manganotify-prod ghcr.io/gregoryn22/manganotify:latest
   docker push ghcr.io/gregoryn22/manganotify:latest
   ```

3. **Update Unraid container:**
   - Go to Unraid Docker tab
   - Click "Force Update" on MangaNotify container
   - Or use `docker-compose pull && docker-compose up -d` on Unraid

## 🔧 Development Tools Setup

### IDE Configuration (VS Code)

Create `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "dev-data/": true
  }
}
```

### Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Development Scripts

Create `scripts/dev-setup.py`:
```python
#!/usr/bin/env python3
"""Development environment setup script."""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    print(f"Running: {description}")
    try:
        subprocess.run(cmd, check=True, shell=True)
        print("✅ Success")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        sys.exit(1)

def main():
    print("Setting up MangaNotify development environment...")
    
    # Install dependencies
    run_command("pip install -r requirements-dev.txt", "Installing development dependencies")
    
    # Create dev data directory
    Path("dev-data").mkdir(exist_ok=True)
    
    # Run initial tests
    run_command("python scripts/run_tests.py --fast", "Running initial tests")
    
    print("🎉 Development environment ready!")
    print("Run: docker-compose -f docker-compose.dev.yml up --build")

if __name__ == "__main__":
    main()
```

## 📁 Directory Structure

```
C:\dev\MangaNotify\
├── src/                    # Source code
├── tests/                  # Test files
├── scripts/                # Development scripts
├── dev-data/               # Development data (gitignored)
├── .env.dev                # Development environment
├── docker-compose.dev.yml  # Development Docker Compose
├── docker-compose.yml      # Production Docker Compose
└── .gitignore              # Git ignore rules
```

## 🔒 Environment Separation

### Development Environment
- **Data**: `./dev-data/` (local, gitignored)
- **Port**: 8999 (local)
- **Polling**: Disabled (`POLL_INTERVAL_SEC=0`)
- **Auth**: Disabled for easier testing
- **Logging**: DEBUG level
- **CORS**: Allows local development ports

### Production Environment
- **Data**: `/mnt/user/appdata/manganotify` (Unraid)
- **Port**: 8999 (exposed)
- **Polling**: Enabled (600 seconds)
- **Auth**: Enabled (if configured)
- **Logging**: INFO level
- **CORS**: Restricted to your domain

## 🚨 Safety Measures

### Git Ignore Rules

Add to `.gitignore`:
```
# Development data
dev-data/
.env.dev
.env.local

# IDE files
.vscode/settings.json
.idea/

# OS files
.DS_Store
Thumbs.db
```

### Backup Strategy

1. **Code**: Git repository (already backed up)
2. **Production Data**: Regular Unraid backups
3. **Development Data**: Local backups (optional)

## 🔄 Migration Plan

### Phase 1: Setup Local Development
1. Move workspace to Windows machine
2. Set up development environment
3. Test local development workflow

### Phase 2: Update Production
1. Ensure production uses published Docker image
2. Set up automated deployment
3. Test production deployment

### Phase 3: Cleanup
1. Remove development files from Unraid
2. Update documentation
3. Train on new workflow

## 🎯 Best Practices

### Development
- ✅ Always test locally before pushing
- ✅ Use feature branches for new features
- ✅ Run full test suite before commits
- ✅ Keep development data separate from production

### Deployment
- ✅ Use automated CI/CD when possible
- ✅ Test Docker builds locally
- ✅ Monitor production logs after deployment
- ✅ Keep production environment minimal

### Code Quality
- ✅ Write tests for new features
- ✅ Use pre-commit hooks
- ✅ Follow consistent code style
- ✅ Document configuration changes

## 🆘 Troubleshooting

### Common Issues

**Docker not starting:**
```bash
# Check Docker Desktop is running
docker --version

# Restart Docker Desktop
# Check WSL2 backend is enabled
```

**Tests failing:**
```bash
# Clean Python cache
find . -name "__pycache__" -delete

# Reinstall dependencies
pip install --force-reinstall -r requirements-dev.txt
```

**Port conflicts:**
```bash
# Check what's using port 8999
netstat -ano | findstr :8999

# Use different port in .env.dev
PORT=8998
```

**Permission issues:**
```bash
# Ensure dev-data directory exists and is writable
mkdir dev-data
chmod 755 dev-data
```

## 📚 Next Steps

1. **Set up local development environment**
2. **Test the new workflow**
3. **Update production deployment**
4. **Document any customizations**
5. **Train team members (if applicable)**

This setup will give you a much more professional and safe development workflow! 🚀
