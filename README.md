# MangaNotify - Manga Tracking & Notification System

A lightweight FastAPI service that monitors manga updates and sends push notifications via Pushover and Discord.

## What is MangaNotify?

MangaNotify is a self-hosted web application that helps you track your favorite manga series and get notified when new chapters are released.

### Key Features
- **Modern Web Interface** - Clean, responsive UI with dark/light theme support
- **Advanced Search** - Find manga by title, status, type, and content rating
- **Watchlist Management** - Easily add/remove manga from your tracking list
- **Real-time Updates** - Automatic background polling for new chapters
- **Smart Notifications** - Get alerts via Pushover (mobile) and Discord
- **Secure** - Optional authentication and comprehensive security features

## Data Attribution

**Important**: MangaNotify uses the [MangaBaka API](https://api.mangabaka.dev) as its data source. Manga data is provided by MangaBaka, which aggregates information from multiple sources including:

- **AniList** - Anime and manga database
- **MyAnimeList** - Community-driven anime and manga database
- **Anime News Network** - Anime and manga news and database
- **MangaUpdates** - Manga database and community
- **Kitsu** - Anime and manga tracking platform
- **Shikimori** - Russian anime and manga database
- **MangaDex** - Manga reading platform

We respect and acknowledge these data sources for providing the comprehensive manga information that makes MangaNotify possible.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- (Optional) Pushover account for mobile notifications
- (Optional) Discord webhook for Discord notifications

### Installation

#### Option 1: Docker Compose (Recommended)
```bash
# Clone the repository
git clone https://github.com/gregoryn22/MangaNotify.git
cd MangaNotify

# Copy environment template
cp env.example .env

# Edit configuration (optional for basic usage)
nano .env

# Run the application
docker-compose up -d

# Access web UI
open http://localhost:8999
```

#### Option 2: Docker Run (Simple)
```bash
# Create data directory
mkdir -p ./manganotify-data

# Run with basic configuration
docker run -d \
  --name manganotify \
  -p 8999:8999 \
  -v ./manganotify-data:/data \
  -e POLL_INTERVAL_SEC=600 \
  ghcr.io/gregoryn22/manganotify:latest
```

### First-time Setup
1. Visit `http://your-server-ip:8999`
2. Use the setup wizard at `http://your-server-ip:8999/setup` to configure notifications and authentication
3. Start adding manga to your watchlist
4. Configure polling interval for automatic updates

## ⚙️ Configuration

MangaNotify uses environment variables for configuration. Copy `env.example` to `.env` and customize as needed.

### Essential Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL_SEC` | `600` | Background polling interval (0=disabled) |
| `AUTH_ENABLED` | `false` | Enable login authentication |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

### Notifications
| Variable | Description | Required |
|----------|-------------|----------|
| `PUSHOVER_APP_TOKEN` | Pushover app token for mobile notifications | Optional |
| `PUSHOVER_USER_KEY` | Your Pushover user key | Optional |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL for notifications | Optional |
| `DISCORD_ENABLED` | Enable Discord notifications (`true`/`false`) | Optional |

### Setting Up Notifications

#### Pushover Setup
1. Create account at [pushover.net](https://pushover.net)
2. Create an application to get your `PUSHOVER_APP_TOKEN`
3. Get your `PUSHOVER_USER_KEY` from your account page
4. Add both to your `.env` file

#### Discord Setup
1. Go to your Discord server settings → Integrations → Webhooks
2. Create a new webhook and copy the URL
3. Set `DISCORD_WEBHOOK_URL` in your `.env` file
4. Set `DISCORD_ENABLED=true`

### Authentication Setup
For production use, enable authentication:

```bash
# Generate a secure secret key (32+ characters)
openssl rand -base64 32

# Hash your password (runs locally, password never leaves your machine)
python scripts/hash_password.py your_password_here

# Alternative: Use any bcrypt tool you prefer
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
```

Add to your `.env`:
```env
AUTH_ENABLED=true
AUTH_SECRET_KEY=your_generated_secret_key_here
AUTH_USERNAME=admin
AUTH_PASSWORD=$2b$12$your_hashed_password_here
```

## API Documentation

### Web Interface
- **Main UI**: `http://your-server:8999` - Full web interface
- **Setup Wizard**: `http://your-server:8999/setup` - Initial configuration

### API Endpoints
- **Health Check**: `GET /api/health` - Service status
- **Search**: `GET /api/search?q=query` - Search manga
- **Series Info**: `GET /api/series/{series_id}` - Get series details
- **Watchlist**: `GET/POST/DELETE /api/watchlist` - Manage watchlist
- **Notifications**: `GET/POST /api/notifications` - Manage notifications

### Example API Usage
```bash
# Search for manga
curl "http://localhost:8999/api/search?q=naruto"

# Get series details
curl "http://localhost:8999/api/series/12345"

# Check health
curl "http://localhost:8999/api/health"
```

## Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker-compose logs manganotify

# Check if port is already in use
netstat -tulpn | grep 8999
```

#### Notifications Not Working
- Verify Pushover credentials are correct
- Test Discord webhook URL manually
- Check logs for notification errors: `docker-compose logs manganotify | grep -i notification`

#### Authentication Issues
- Ensure `AUTH_SECRET_KEY` is at least 32 characters long
- Use the password hashing script: `python scripts/hash_password.py your_password`
- Check that `AUTH_ENABLED=true` is set correctly

### Getting Help
1. Check the logs first: `docker-compose logs manganotify`
2. Search existing [GitHub Issues](https://github.com/gregoryn22/MangaNotify/issues)
3. Create a new issue with logs and configuration details

## Security

MangaNotify includes comprehensive security features:
- **Optional authentication** with JWT tokens
- **Rate limiting** to prevent abuse
- **Security headers** (CSP, HSTS, XSS protection)
- **Input validation** and sanitization
- **CSRF protection** with origin validation

For production deployments, see `SECURITY.md` for detailed security configuration and best practices.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/run_tests.py`
5. Submit a pull request

## License

See `LICENSE` file for details.

---

## Development

### Local environment setup

Install both the runtime and development dependencies to ensure the full test suite (including async tests) is available:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

This installs tooling such as `pytest-asyncio`, which is required for the asynchronous tests in this project.

### Project Structure
```
src/manganotify/
├── core/           # Core configuration and utilities
├── models/         # Pydantic data models
├── routers/        # FastAPI route handlers
├── services/       # Business logic (API, notifications, polling)
├── storage/        # Data persistence layer
├── static/         # Web UI assets (HTML, CSS, JS)
└── main.py         # Application entry point
```

### Testing
```bash
# Run tests with coverage
python scripts/run_tests.py --coverage

# Run specific test file
python -m pytest tests/test_auth.py -v

# Test Docker build
docker build -t manganotify-test .
docker run --rm -p 8999:8999 manganotify-test
```

### Deployment
```bash
# Push to trigger GitHub Actions build
git add .
git commit -m "Your changes"
git push origin master

# GitHub Actions will automatically build and publish to GHCR
```