# Security Guide for MangaNotify

## 🔒 Production Security Checklist

### ✅ Authentication & Authorization
- [ ] **Enable authentication** (`AUTH_ENABLED=true`)
- [ ] **Use strong JWT secret** (minimum 32 characters)
- [ ] **Use strong password** (minimum 8 characters, avoid common passwords)
- [ ] **Set appropriate token expiration** (default: 24 hours)

### ✅ Network Security
- [ ] **Configure CORS properly** - Change `CORS_ALLOW_ORIGINS` from `*` to your domain
- [ ] **Use HTTPS** with valid SSL certificate
- [ ] **Set up reverse proxy** (Nginx/Apache) with security headers
- [ ] **Configure firewall** to restrict access

### ✅ Application Security
- [ ] **Keep dependencies updated** (`pip install -r requirements.txt --upgrade`)
- [ ] **Use secure environment variables** (never commit `.env` to version control)
- [ ] **Enable logging** and monitor for suspicious activity
- [ ] **Regular security audits** of your deployment

## 🛡️ Security Features Implemented

### Authentication & Session Management
- **JWT-based authentication** with secure secret keys
- **Bcrypt password hashing** with salt
- **Token expiration** and validation
- **Rate limiting** on login attempts (5 per minute per IP)
- **Generic error messages** to prevent username enumeration

### Input Validation & Sanitization
- **Pydantic model validation** for all API endpoints
- **Query parameter validation** with length limits
- **Regex validation** for usernames and URLs
- **SQL injection prevention** through parameterized queries
- **XSS protection** through input sanitization

### HTTP Security Headers
- **Content Security Policy (CSP)** - Strict for production
- **X-Content-Type-Options: nosniff** - Prevents MIME sniffing
- **X-Frame-Options: DENY** - Prevents clickjacking
- **X-XSS-Protection: 1; mode=block** - XSS protection
- **Referrer-Policy: strict-origin-when-cross-origin** - Controls referrer
- **Permissions-Policy** - Restricts browser features
- **Strict-Transport-Security** - HSTS for HTTPS

### CSRF Protection
- **Origin header validation** for state-changing requests
- **CORS configuration** with specific allowed origins
- **SameSite cookie attributes** (when using cookies)

### Rate Limiting
- **Login attempts**: 5 per minute per IP
- **API requests**: 100 per minute per IP
- **Automatic cleanup** of old rate limit entries
- **IP-based tracking** with X-Forwarded-For support

### Data Protection
- **Encrypted credential storage** using AES-256
- **PBKDF2 key derivation** with 100,000 iterations
- **Secure random key generation** for encryption
- **File system permissions** validation

## 🚨 Security Vulnerabilities Fixed

### Critical Issues Resolved
1. **Information Disclosure** - Debug endpoint now requires authentication
2. **CSRF Attacks** - Added origin header validation
3. **Rate Limiting** - Implemented functional rate limiting
4. **CORS Misconfiguration** - Default changed from `*` to specific domain
5. **Missing CSP** - Added Content Security Policy headers
6. **Weak Input Validation** - Enhanced with regex and length limits
7. **JWT Algorithm Validation** - Added header validation to prevent algorithm confusion attacks
8. **Path Traversal** - Implemented secure static file serving with path validation
9. **Request Size DoS** - Added 10MB request size limit
10. **SSRF Protection** - Restricted external API calls to known domains
11. **Silent Crypto Failures** - Enhanced error handling in credential decryption
12. **Missing Security Headers** - Added security headers to static files
13. **API Documentation Exposure** - Disabled docs/redoc in production
14. **Weak Password Detection** - Enhanced password strength validation
15. **Open Search Endpoint** - Added authentication requirement to search API
16. **Open Series Endpoint** - Added authentication requirement to series API
17. **Missing Input Length Limits** - Added max_length validation to all query parameters
18. **Missing Parameter Range Validation** - Added ge/le validation to numeric parameters
19. **Missing Filter Sanitization** - Added regex validation to filter parameters
20. **Missing Search Rate Limiting** - Added specific rate limiting for search endpoint
21. **Enhanced Password Validation** - Added password pattern detection and username comparison
22. **Notification Credential Validation** - Added length and format validation for notification tokens
23. **Startup Security Validation** - Added comprehensive validation on application startup
24. **Enhanced Rate Limiting** - Added specific limits for different endpoint types
25. **Open Setup Endpoints** - Added authentication requirement to all setup endpoints
26. **Missing Setup Rate Limiting** - Added specific rate limiting for setup endpoints
27. **Missing Master Key Validation** - Added length and format validation for master keys
28. **Missing Configuration Validation** - Added validation for port, poll interval, and token expiration
29. **Enhanced Authentication Validation** - Added comprehensive input validation in authenticate_user
30. **Enhanced Crypto Validation** - Added master key and credential length validation
31. **XSS Vulnerabilities in Frontend** - Added input sanitization to prevent XSS attacks
32. **Information Disclosure in Console Logs** - Removed sensitive information from console logs
33. **Missing Input Sanitization** - Added HTML entity escaping for user input
34. **Missing Log Level Validation** - Added validation for LOG_LEVEL and LOG_FORMAT
35. **Enhanced JWT Token Validation** - Added comprehensive validation for JWT token creation
36. **Missing Username Validation in Tokens** - Added username format validation in token creation

### Security Headers Added
- Content Security Policy (CSP)
- Strict Transport Security (HSTS)
- Enhanced Permissions Policy
- Improved Referrer Policy
- X-Content-Type-Options for static files
- X-Frame-Options for static files
- Cache-Control for static assets

### Additional Security Measures
- **JWT Algorithm Validation** - Prevents algorithm confusion attacks
- **Path Traversal Protection** - Secure static file serving
- **Request Size Limiting** - 10MB limit to prevent DoS
- **SSRF Protection** - Domain whitelist for external API calls
- **Enhanced Crypto Error Handling** - Proper logging without information disclosure
- **Production API Documentation** - Disabled in production mode
- **Password Strength Validation** - Enhanced weak password detection
- **Comprehensive Input Validation** - All parameters validated with length and format limits
- **Authentication on All Endpoints** - All endpoints now require authentication
- **Enhanced Rate Limiting** - Specific limits for different endpoint types
- **Startup Security Validation** - Comprehensive validation on application startup
- **Notification Credential Validation** - Length and format validation for all notification tokens
- **Setup Endpoint Security** - All setup endpoints now require authentication
- **Master Key Validation** - Length and format validation for encryption keys
- **Configuration Validation** - Port, poll interval, and token expiration validation
- **Enhanced Authentication Validation** - Comprehensive input validation in authentication
- **Enhanced Crypto Validation** - Master key and credential length validation
- **Frontend XSS Protection** - Input sanitization and HTML entity escaping
- **Information Disclosure Prevention** - Removed sensitive information from console logs
- **Log Configuration Validation** - Validation for log level and format settings
- **Enhanced JWT Security** - Comprehensive validation for JWT token creation
- **Username Validation in Tokens** - Format validation for usernames in JWT tokens

## 🔧 Reverse Proxy Configuration

### Nginx Example
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'" always;
    
    # Proxy to MangaNotify
    location / {
        proxy_pass http://localhost:8999;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### Apache Example
```apache
<VirtualHost *:443>
    ServerName yourdomain.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /path/to/cert.pem
    SSLCertificateKeyFile /path/to/key.pem
    
    # Security Headers
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'"
    
    # Proxy to MangaNotify
    ProxyPreserveHost On
    ProxyPass / http://localhost:8999/
    ProxyPassReverse / http://localhost:8999/
</VirtualHost>
```

## 🔍 Monitoring & Logging

### Security Logging
- **Failed login attempts** logged with IP addresses
- **Rate limit violations** logged with timestamps
- **CSRF protection violations** logged with origins
- **Request correlation IDs** for tracking

### Monitoring Recommendations
- **Set up log aggregation** (ELK stack, Splunk, etc.)
- **Monitor for suspicious patterns** (multiple failed logins, unusual traffic)
- **Set up alerts** for security events
- **Regular log review** for anomalies

## 🚀 Deployment Security

### Environment Variables
```bash
# Required for production
AUTH_ENABLED=true
AUTH_USERNAME=your_username
AUTH_PASSWORD=$2b$12$...  # Use setup wizard to generate
AUTH_SECRET_KEY=...        # Use setup wizard to generate
CORS_ALLOW_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO

# Optional but recommended
MASTER_KEY=...             # For encrypted credentials
PUSHOVER_APP_TOKEN=...     # Encrypted
PUSHOVER_USER_KEY=...      # Encrypted
DISCORD_WEBHOOK_URL=...    # Encrypted
```

### Docker Security
- **Use non-root user** in container
- **Limit container capabilities**
- **Use read-only filesystem** where possible
- **Regular base image updates**

### File Permissions
```bash
# Secure .env file
chmod 600 .env
chown root:root .env

# Secure data directory
chmod 755 data/
chown app:app data/
```

## 📋 Security Testing

### Manual Testing Checklist
- [ ] **Authentication bypass** attempts
- [ ] **SQL injection** attempts
- [ ] **XSS** attempts
- [ ] **CSRF** attempts
- [ ] **Rate limiting** verification
- [ ] **File upload** security (if applicable)
- [ ] **Directory traversal** attempts

### Automated Testing
- **OWASP ZAP** for web application security testing
- **Burp Suite** for comprehensive security testing
- **Nmap** for network security scanning
- **SSL Labs** for SSL/TLS configuration testing

## 🆘 Incident Response

### Security Incident Checklist
1. **Identify** the scope and impact
2. **Contain** the incident (disable affected services)
3. **Investigate** root cause and timeline
4. **Eradicate** the threat
5. **Recover** services securely
6. **Document** lessons learned
7. **Update** security measures

### Emergency Contacts
- **Security Team**: [your-security-team@company.com]
- **System Administrator**: [admin@company.com]
- **Incident Response**: [incident@company.com]

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Nginx Security Headers](https://nginx.org/en/docs/http/ngx_http_headers_module.html)
- [SSL/TLS Configuration Guide](https://ssl-config.mozilla.org/)

---

**Remember**: Security is an ongoing process, not a one-time setup. Regular updates, monitoring, and testing are essential for maintaining a secure deployment.
