# Security Guide for MangaNotify

## 🔒 Production Security Checklist

### ✅ Essential Security Settings
- [ ] **Enable authentication** (`AUTH_ENABLED=true`)
- [ ] **Use strong JWT secret** (minimum 32 characters)
- [ ] **Use strong password** (minimum 8 characters)
- [ ] **Configure CORS properly** - Change `CORS_ALLOW_ORIGINS` from `*` to your domain
- [ ] **Use HTTPS** with valid SSL certificate
- [ ] **Keep dependencies updated**

### ✅ Optional but Recommended
- [ ] **Set up reverse proxy** (Nginx/Apache) with security headers
- [ ] **Configure firewall** to restrict access
- [ ] **Enable logging** and monitor for suspicious activity

## 🛡️ Security Features Implemented

### Authentication & Session Management
- **JWT-based authentication** with secure secret keys
- **Bcrypt password hashing** with salt
- **Token expiration** and validation
- **Rate limiting** on login attempts (10 per minute per IP)
- **Generic error messages** to prevent username enumeration

### HTTP Security Headers
- **Content Security Policy (CSP)** - Strict for production
- **X-Content-Type-Options: nosniff** - Prevents MIME sniffing
- **X-Frame-Options: DENY** - Prevents clickjacking
- **X-XSS-Protection: 1; mode=block** - XSS protection
- **Referrer-Policy: strict-origin-when-cross-origin** - Controls referrer
- **Strict-Transport-Security** - HSTS for HTTPS

### Input Validation & Protection
- **Pydantic model validation** for all API endpoints
- **Query parameter validation** with length limits
- **CSRF protection** with origin header validation
- **Rate limiting** on API endpoints (100 per minute per IP)
- **Request size limiting** (10MB limit)

## 🔧 Quick Setup for Production

### Environment Variables
```bash
# Required for production
AUTH_ENABLED=true
AUTH_USERNAME=your_username
AUTH_PASSWORD=$2b$12$...  # Use setup wizard to generate
AUTH_SECRET_KEY=...        # Use setup wizard to generate
CORS_ALLOW_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

### Simple Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy to MangaNotify
    location / {
        proxy_pass http://localhost:8999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🚨 Common Security Issues

### Authentication Problems
- **Weak secret key**: Use `openssl rand -base64 32` to generate
- **Plain text password**: Use the setup wizard to hash your password
- **Missing authentication**: Set `AUTH_ENABLED=true` in production

### CORS Issues
- **Wildcard CORS**: Change `CORS_ALLOW_ORIGINS` from `*` to your domain
- **Missing HTTPS**: Use HTTPS in production

### Rate Limiting
- **Too many requests**: Default is 100 requests per minute per IP
- **Login attempts**: Limited to 10 per minute per IP

## 🔍 Monitoring

### Basic Logging
```bash
# Check for failed login attempts
docker-compose logs manganotify | grep -i "login"

# Check for rate limiting
docker-compose logs manganotify | grep -i "rate limit"

# Monitor general activity
docker-compose logs -f manganotify
```

### Security Alerts
- Monitor for multiple failed login attempts
- Watch for unusual traffic patterns
- Check for authentication bypass attempts

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Nginx Security Headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html)

---

**Note**: This is a self-hosted application. Security is your responsibility. Start with the essential checklist and add more measures as needed.