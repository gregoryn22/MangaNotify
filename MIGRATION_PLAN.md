# Migration Plan: From Mixed Dev/Prod to Separated Environments

This guide provides a step-by-step plan to migrate from your current mixed development/production setup to a clean, separated environment structure.

## 🎯 Migration Goals

### Current State
- ❌ Development and production mixed on Unraid server
- ❌ Risk of accidentally affecting production during development
- ❌ Slower development cycle due to network latency
- ❌ Harder to experiment safely

### Target State
- ✅ **Local development** on Windows machine
- ✅ **Clean production** on Unraid server
- ✅ **Automated deployment** via GitHub Actions
- ✅ **Safe experimentation** without production risk
- ✅ **Faster development** cycle

## 📋 Pre-Migration Checklist

Before starting the migration, ensure you have:

- [ ] **Docker Desktop** installed on Windows machine
- [ ] **Git** installed and configured
- [ ] **Backup** of current production data
- [ ] **Access** to Unraid server
- [ ] **GitHub repository** with Actions enabled
- [ ] **Time** for the migration (2-3 hours)

## 🚀 Migration Steps

### Phase 1: Setup Local Development Environment

#### Step 1.1: Prepare Windows Machine
```bash
# Create development directory
mkdir C:\dev\MangaNotify
cd C:\dev\MangaNotify

# Clone repository
git clone https://github.com/gregoryn22/MangaNotify.git .

# Verify clone
git status
```

#### Step 1.2: Install Dependencies
```bash
# Install Python dependencies
pip install -r requirements-dev.txt

# Verify Docker Desktop is running
docker --version
docker-compose --version
```

#### Step 1.3: Setup Development Environment
```bash
# Run setup script
python scripts/dev-setup.py

# Create development environment file
cp env.dev.example .env.dev

# Customize .env.dev for your needs
# (Edit the file with your preferred settings)
```

#### Step 1.4: Test Local Development
```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Test in browser: http://localhost:8999
# Run tests
python scripts/run_tests.py --fast

# Stop development environment
docker-compose -f docker-compose.dev.yml down
```

**✅ Phase 1 Complete**: Local development environment is working

### Phase 2: Backup and Prepare Production

#### Step 2.1: Backup Production Data
```bash
# SSH into Unraid server
ssh root@your-unraid-server

# Navigate to appdata directory
cd /mnt/user/appdata/manganotify

# Create backup
cp -r data data-backup-$(date +%Y%m%d-%H%M%S)

# Verify backup
ls -la data-backup-*
```

#### Step 2.2: Document Current Production Settings
```bash
# Check current environment variables
docker inspect manganotify | grep -A 20 "Env"

# Document current configuration
# (Save this information for reference)
```

#### Step 2.3: Prepare Production Environment File
```bash
# Create production environment file
cp env.example .env.prod

# Edit .env.prod with your production settings
# (Use the documented settings from Step 2.2)
```

**✅ Phase 2 Complete**: Production data backed up and documented

### Phase 3: Update Production Deployment

#### Step 3.1: Ensure GitHub Actions is Working
```bash
# Push a small test change
echo "# Test deployment" >> README.md
git add README.md
git commit -m "Test: Verify GitHub Actions deployment"
git push origin main

# Check GitHub Actions tab for successful run
# Verify Docker image was published to GHCR
```

#### Step 3.2: Update Unraid Container Configuration
```bash
# SSH into Unraid server
ssh root@your-unraid-server

# Navigate to appdata directory
cd /mnt/user/appdata/manganotify

# Update docker-compose.yml to use published image
# Change from:
#   build: .
# To:
#   image: ghcr.io/gregoryn22/manganotify:latest

# Update environment file
cp .env.prod .env
```

#### Step 3.3: Test Production Deployment
```bash
# Pull latest image
docker-compose pull

# Restart container
docker-compose down
docker-compose up -d

# Verify container is running
docker ps | grep manganotify

# Test endpoints
curl http://localhost:8999/api/health
```

**✅ Phase 3 Complete**: Production using automated deployment

### Phase 4: Clean Up Development Files from Production

#### Step 4.1: Remove Development Files from Unraid
```bash
# SSH into Unraid server
ssh root@your-unraid-server

# Navigate to appdata directory
cd /mnt/user/appdata/manganotify

# Remove development files (keep only production files)
rm -rf src/
rm -rf tests/
rm -rf scripts/
rm -rf .github/
rm -rf htmlcov/
rm -rf images/
rm -rf unraid/
rm -f *.md
rm -f *.txt
rm -f *.ini
rm -f Dockerfile
rm -f docker-compose.dev.yml
rm -f env.dev.example

# Keep only production files:
# - docker-compose.yml
# - .env
# - data/
# - data-backup-*/
```

#### Step 4.2: Verify Production Still Works
```bash
# Test production functionality
curl http://your-unraid-server:8999/api/health
curl http://your-unraid-server:8999/api/watchlist

# Check logs
docker logs manganotify
```

**✅ Phase 4 Complete**: Production environment cleaned up

### Phase 5: Final Testing and Validation

#### Step 5.1: Test Complete Workflow
```bash
# On Windows machine (local development)
cd C:\dev\MangaNotify

# Make a small change
echo "# Updated from local development" >> README.md

# Run tests
python scripts/run_tests.py

# Commit and push
git add README.md
git commit -m "Test: Complete workflow from local development"
git push origin main

# Wait for GitHub Actions to complete
# Check that new image was published
```

#### Step 5.2: Verify Production Update
```bash
# SSH into Unraid server
ssh root@your-unraid-server

# Navigate to appdata directory
cd /mnt/user/appdata/manganotify

# Pull latest image
docker-compose pull

# Restart container
docker-compose up -d

# Verify update worked
docker logs manganotify | tail -20
```

#### Step 5.3: Test Rollback Procedure
```bash
# Test rollback capability
# (This ensures you can recover if something goes wrong)

# Create a rollback tag
git tag rollback-test-$(date +%Y%m%d-%H%M%S) HEAD~1
git push origin rollback-test-$(date +%Y%m%d-%H%M%S)

# Verify rollback image was built
# (Check GitHub Actions and GHCR)
```

**✅ Phase 5 Complete**: Complete workflow tested and validated

## 🔄 Post-Migration Workflow

### Daily Development Process
```bash
# 1. Start development environment
cd C:\dev\MangaNotify
docker-compose -f docker-compose.dev.yml up --build

# 2. Make changes and test locally
# 3. Run tests
python scripts/run_tests.py

# 4. Commit and push
git add .
git commit -m "Your changes"
git push origin main

# 5. Wait for automated deployment
# 6. Verify production update
```

### Emergency Procedures
```bash
# If production has issues:

# 1. Quick rollback via GitHub
git tag rollback-$(date +%Y%m%d-%H%M%S) HEAD~1
git push origin rollback-$(date +%Y%m%d-%H%M%S)

# 2. Or manual rollback
docker pull ghcr.io/gregoryn22/manganotify:previous-tag
# Update Unraid container to use previous tag
```

## 🚨 Troubleshooting Migration Issues

### Common Issues and Solutions

#### Issue: Local development won't start
```bash
# Check Docker Desktop is running
docker --version

# Check ports are available
netstat -ano | findstr :8999

# Clean up any existing containers
docker-compose -f docker-compose.dev.yml down
docker system prune -f
```

#### Issue: Production container won't update
```bash
# Check image exists in registry
docker pull ghcr.io/gregoryn22/manganotify:latest

# Check Unraid container configuration
docker-compose config

# Force update
docker-compose pull
docker-compose up -d --force-recreate
```

#### Issue: GitHub Actions failing
```bash
# Check Actions tab in GitHub
# Look for specific error messages
# Common issues:
# - Missing environment variables
# - Test failures
# - Docker build issues
```

#### Issue: Data loss concerns
```bash
# Verify backups exist
ls -la /mnt/user/appdata/manganotify/data-backup-*

# Restore from backup if needed
cp -r data-backup-YYYYMMDD-HHMMSS/* data/
```

### Recovery Procedures

#### Complete Rollback to Previous Setup
```bash
# If migration fails completely:

# 1. Stop new container
docker-compose down

# 2. Restore from backup
cp -r data-backup-YYYYMMDD-HHMMSS/* data/

# 3. Revert to build-based deployment
# Edit docker-compose.yml to use "build: ." instead of image
# Restore source files from backup

# 4. Restart container
docker-compose up -d --build
```

## 📊 Migration Validation Checklist

After migration, verify:

- [ ] **Local development** works (`docker-compose -f docker-compose.dev.yml up`)
- [ ] **Tests pass** locally (`python scripts/run_tests.py`)
- [ ] **Production** is accessible (`curl http://your-unraid-server:8999/api/health`)
- [ ] **Automated deployment** works (push to GitHub triggers deployment)
- [ ] **Data integrity** maintained (watchlist, notifications preserved)
- [ ] **Rollback procedure** tested and working
- [ ] **Documentation** updated with new workflow
- [ ] **Backup procedures** in place

## 🎯 Benefits After Migration

### Development Benefits
- ✅ **Faster iteration** - No network latency
- ✅ **Safer experimentation** - Can't break production
- ✅ **Better debugging** - Full IDE integration
- ✅ **Easier testing** - Run tests locally before deployment

### Production Benefits
- ✅ **Automated deployment** - No manual steps
- ✅ **Consistent builds** - Same process every time
- ✅ **Easy rollbacks** - Via Docker image tags
- ✅ **Audit trail** - All deployments tracked

### Operational Benefits
- ✅ **Cleaner separation** - Dev and prod environments isolated
- ✅ **Better monitoring** - Clear production logs
- ✅ **Easier maintenance** - Standardized procedures
- ✅ **Reduced risk** - Less chance of production issues

## 📚 Next Steps After Migration

1. **Document the new workflow** for your team
2. **Set up monitoring** for production
3. **Create deployment scripts** for common tasks
4. **Train on new procedures** if you have team members
5. **Plan regular maintenance** tasks

## 🆘 Getting Help

If you encounter issues during migration:

1. **Check the logs** - Both local and production
2. **Review the documentation** - Development and deployment guides
3. **Test incrementally** - Don't try to migrate everything at once
4. **Keep backups** - Always have a rollback plan
5. **Ask for help** - Post issues on GitHub or community forums

The migration will give you a much more professional and maintainable development workflow! 🚀
