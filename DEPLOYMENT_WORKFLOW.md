# Deployment Workflow Guide for MangaNotify

This guide explains the recommended deployment workflow for MangaNotify, covering both automated and manual deployment options.

## 🎯 Deployment Strategy Overview

### Current Setup Analysis
- **Development**: Currently mixed with production on Unraid
- **Production**: Docker container on Unraid server
- **CI/CD**: GitHub Actions workflows already configured
- **Registry**: GitHub Container Registry (GHCR)

### Recommended Approach
- **Development**: Local Windows machine with Docker Desktop
- **Production**: Automated deployment to Unraid via GitHub Actions
- **Testing**: Local testing before deployment
- **Rollback**: Easy rollback via Docker image tags

## 🚀 Deployment Workflows

### Option 1: Automated Deployment (Recommended)

This is the safest and most efficient approach:

#### Workflow Steps
1. **Develop locally** on Windows machine
2. **Test locally** with Docker
3. **Commit and push** to GitHub
4. **GitHub Actions** automatically:
   - Runs full test suite
   - Builds Docker image
   - Publishes to GHCR
   - Updates Unraid container

#### Benefits
- ✅ **Automated testing** before deployment
- ✅ **Consistent builds** every time
- ✅ **Easy rollbacks** via image tags
- ✅ **No manual steps** to forget
- ✅ **Audit trail** of all deployments

#### Setup Requirements
- GitHub repository with Actions enabled
- Unraid container configured to use GHCR image
- Proper environment variables set

### Option 2: Manual Deployment

For when you need more control or want to test specific changes:

#### Workflow Steps
1. **Develop and test locally**
2. **Build production image** locally
3. **Push to registry** manually
4. **Update Unraid container** manually

#### When to Use
- Testing specific configurations
- Emergency hotfixes
- When automated deployment fails
- Learning/testing deployment process

## 📋 Detailed Deployment Procedures

### Automated Deployment Setup

#### 1. Configure GitHub Actions

Your existing workflows should handle this, but verify:

```yaml
# .github/workflows/docker-publish.yml
name: Docker Publish
on:
  push:
    branches: [main, master]
  workflow_dispatch:

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run tests
        run: python scripts/run_tests.py --coverage
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/gregoryn22/manganotify:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

#### 2. Configure Unraid Container

Update your Unraid container to use the published image:

```xml
<!-- unraid/manganotify.xml -->
<Container>
  <Name>MangaNotify</Name>
  <Repository>ghcr.io/gregoryn22/manganotify:latest</Repository>
  <Registry>https://github.com/gregoryn22/MangaNotify/pkgs/container/manganotify</Registry>
  <!-- ... other settings ... -->
</Container>
```

#### 3. Set Up Environment Variables

Create a `.env` file on Unraid with production settings:

```env
# Production Environment
MANGABAKA_BASE=https://api.mangabaka.dev
PORT=8999
DATA_DIR=/data
POLL_INTERVAL_SEC=600

# CORS - Restrict to your domain
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Authentication
AUTH_ENABLED=true
AUTH_SECRET_KEY=your-secure-secret-key
AUTH_USERNAME=admin
AUTH_PASSWORD=your-secure-password
AUTH_TOKEN_EXPIRE_HOURS=24

# Notifications
PUSHOVER_APP_TOKEN=your-app-token
PUSHOVER_USER_KEY=your-user-key
DISCORD_ENABLED=false
DISCORD_WEBHOOK_URL=

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=plain

# Timezone
TZ=America/New_York
```

### Manual Deployment Process

#### 1. Local Development and Testing

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Run tests
python scripts/run_tests.py --coverage --verbose

# Test production build locally
docker build -t manganotify-test .
docker run --rm -p 8999:8999 \
  -e POLL_INTERVAL_SEC=0 \
  -e AUTH_ENABLED=false \
  manganotify-test
```

#### 2. Build Production Image

```bash
# Build production image
docker build -t manganotify-prod .

# Tag for registry
docker tag manganotify-prod ghcr.io/gregoryn22/manganotify:latest
docker tag manganotify-prod ghcr.io/gregoryn22/manganotify:$(git rev-parse --short HEAD)
```

#### 3. Push to Registry

```bash
# Login to GHCR (if not already logged in)
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Push images
docker push ghcr.io/gregoryn22/manganotify:latest
docker push ghcr.io/gregoryn22/manganotify:$(git rev-parse --short HEAD)
```

#### 4. Update Unraid Container

**Option A: Via Unraid Web UI**
1. Go to Docker tab
2. Find MangaNotify container
3. Click "Force Update"
4. Restart container

**Option B: Via SSH/Command Line**
```bash
# SSH into Unraid
ssh root@your-unraid-server

# Navigate to appdata directory
cd /mnt/user/appdata/manganotify

# Pull latest image
docker-compose pull

# Restart container
docker-compose up -d
```

## 🔄 Rollback Procedures

### Quick Rollback (Automated)

If you have automated deployment, rollback is easy:

```bash
# Create a rollback tag
git tag rollback-$(date +%Y%m%d-%H%M%S) HEAD~1
git push origin rollback-$(date +%Y%m%d-%H%M%S)

# GitHub Actions will build and deploy the rollback
```

### Manual Rollback

```bash
# Find the previous working image
docker images ghcr.io/gregoryn22/manganotify

# Tag the previous image as latest
docker tag ghcr.io/gregoryn22/manganotify:previous-tag ghcr.io/gregoryn22/manganotify:latest

# Push the rollback
docker push ghcr.io/gregoryn22/manganotify:latest

# Update Unraid container
# (Same process as manual deployment)
```

## 🧪 Testing Before Deployment

### Pre-deployment Checklist

- [ ] **Local tests pass**: `python scripts/run_tests.py`
- [ ] **Docker build succeeds**: `docker build -t test .`
- [ ] **Container starts**: `docker run --rm test`
- [ ] **Health check passes**: `curl http://localhost:8999/api/health`
- [ ] **Configuration validated**: Check all environment variables
- [ ] **Dependencies updated**: Review `requirements.txt` changes
- [ ] **Documentation updated**: Update README if needed

### Testing Commands

```bash
# Full test suite
python scripts/run_tests.py --coverage --verbose

# Specific test categories
python scripts/run_tests.py --poller --api

# Docker functionality
docker build -t manganotify-test .
docker run --rm -p 8999:8999 \
  -e POLL_INTERVAL_SEC=0 \
  -e AUTH_ENABLED=false \
  manganotify-test &

# Test endpoints
curl http://localhost:8999/api/health
curl http://localhost:8999/api/watchlist

# Cleanup
docker stop $(docker ps -q --filter ancestor=manganotify-test)
```

## 📊 Monitoring and Validation

### Post-deployment Checks

1. **Container Status**
   ```bash
   docker ps | grep manganotify
   docker logs manganotify
   ```

2. **Health Endpoints**
   ```bash
   curl http://your-unraid-server:8999/api/health
   curl http://your-unraid-server:8999/api/health/details
   ```

3. **Application Logs**
   ```bash
   docker logs -f manganotify
   ```

4. **Functionality Tests**
   - Access web UI
   - Test watchlist operations
   - Verify notification settings
   - Check polling status

### Monitoring Setup

Consider setting up monitoring for:

- **Container health**: Docker health checks
- **Application metrics**: Response times, error rates
- **Resource usage**: CPU, memory, disk
- **Log monitoring**: Error patterns, warnings
- **Notification delivery**: Success/failure rates

## 🚨 Troubleshooting Deployment Issues

### Common Issues

#### Container Won't Start
```bash
# Check logs
docker logs manganotify

# Check configuration
docker run --rm ghcr.io/gregoryn22/manganotify:latest env

# Test with minimal config
docker run --rm -p 8999:8999 \
  -e POLL_INTERVAL_SEC=0 \
  -e AUTH_ENABLED=false \
  ghcr.io/gregoryn22/manganotify:latest
```

#### Image Pull Failures
```bash
# Check registry access
docker pull ghcr.io/gregoryn22/manganotify:latest

# Verify authentication
docker login ghcr.io

# Check image exists
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://ghcr.io/v2/gregoryn22/manganotify/manifests/latest
```

#### Configuration Issues
```bash
# Validate environment variables
docker run --rm ghcr.io/gregoryn22/manganotify:latest python -c "
import os
from manganotify.core.config import get_settings
settings = get_settings()
print('Configuration loaded successfully')
print(f'Data dir: {settings.data_dir}')
print(f'Poll interval: {settings.poll_interval_sec}')
"
```

### Emergency Procedures

#### Quick Fix Deployment
```bash
# Build and deploy hotfix locally
git checkout hotfix-branch
docker build -t manganotify-hotfix .
docker tag manganotify-hotfix ghcr.io/gregoryn22/manganotify:hotfix
docker push ghcr.io/gregoryn22/manganotify:hotfix

# Update Unraid to use hotfix
# Change repository to ghcr.io/gregoryn22/manganotify:hotfix
```

#### Complete Rollback
```bash
# Stop current container
docker stop manganotify

# Remove current container
docker rm manganotify

# Pull previous working image
docker pull ghcr.io/gregoryn22/manganotify:previous-tag

# Start with previous image
docker run -d --name manganotify \
  -p 8999:8999 \
  -v manganotify-data:/data \
  ghcr.io/gregoryn22/manganotify:previous-tag
```

## 📈 Best Practices

### Development
- ✅ **Test locally** before pushing
- ✅ **Use feature branches** for new features
- ✅ **Run full test suite** before commits
- ✅ **Keep development data separate** from production

### Deployment
- ✅ **Use automated deployment** when possible
- ✅ **Test Docker builds** locally
- ✅ **Monitor logs** after deployment
- ✅ **Have rollback plan** ready

### Production
- ✅ **Monitor application health**
- ✅ **Keep backups** of production data
- ✅ **Document configuration changes**
- ✅ **Test rollback procedures** regularly

## 🔧 Customization

### Environment-specific Configurations

Create different configurations for different environments:

```bash
# Development
cp env.dev.example .env.dev

# Staging (if needed)
cp env.example .env.staging

# Production
cp env.example .env.prod
```

### Custom Deployment Scripts

Create deployment scripts for common tasks:

```bash
#!/bin/bash
# scripts/deploy.sh

set -e

echo "Starting deployment..."

# Run tests
python scripts/run_tests.py

# Build image
docker build -t manganotify-prod .

# Push to registry
docker push ghcr.io/gregoryn22/manganotify:latest

# Update production
echo "Deployment complete!"
echo "Update your Unraid container to pull the latest image."
```

## 📚 Next Steps

1. **Set up automated deployment** using GitHub Actions
2. **Test the deployment process** with a small change
3. **Set up monitoring** for production
4. **Document any customizations** you make
5. **Train team members** on the new workflow

This deployment workflow will give you confidence in your releases and make maintenance much easier! 🚀
