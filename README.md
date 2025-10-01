# MangaNotify - Manga Tracking & Notification System

A lightweight FastAPI service that monitors manga updates from the MangaBaka API and sends push notifications via Pushover and Discord.

## 🚀 Quick Start

### Local Development
```bash
# Clone and setup
git clone https://github.com/gregoryn22/MangaNotify.git
cd MangaNotify

# Run with Docker
docker-compose -f docker-compose.dev.yml up --build

# Access web UI
open http://localhost:8999
```

### Production Deployment (Unraid)
1. Use the provided `unraid/manganotify.xml` template
2. Set up environment variables (see Configuration section)
3. Fix permissions: `chown -R 10001:10001 /mnt/user/appdata/manganotify`

## ⚙️ Configuration

### Environment Variables
- `PUSHOVER_APP_TOKEN` - Pushover app token for mobile notifications
- `PUSHOVER_USER_KEY` - Pushover user key
- `DISCORD_WEBHOOK_URL` - Discord webhook URL
- `AUTH_ENABLED` - Enable authentication (recommended for production)
- `POLL_INTERVAL_SEC` - Polling interval in seconds (0=disabled)

### Unraid Setup
The `unraid/manganotify.xml` provides a comprehensive template with all configuration options.

## 🔧 Development

### Testing
```bash
# Run tests
python scripts/run_tests.py --coverage

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

## 📚 Features

- 📱 **Modern Web UI** - Responsive design with dark/light themes
- 🔔 **Multi-channel Notifications** - Pushover & Discord support
- 🔐 **Authentication** - Optional login protection
- ⚡ **Real-time Updates** - Automatic polling and notifications
- 📊 **Watchlist Management** - Track your favorite manga
- 🔍 **Advanced Search** - Filter by status, type, content rating
- 📱 **PWA Support** - Mobile app-like experience

## 🛡️ Security

See `SECURITY.md` for detailed security information and best practices.

## 📖 API Documentation

Once running, visit:
- Web UI: `http://your-server:8999`
- Health Check: `http://your-server:8999/api/health`
- API Docs: `http://your-server:8999/docs`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python scripts/run_tests.py`
5. Submit a pull request

## 📄 License

See `LICENSE` file for details.