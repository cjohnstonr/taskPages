"""
Secure configuration for Google OAuth + Flask + Redis
All security best practices implemented
"""
import os
from datetime import timedelta
from urllib.parse import urlparse, urljoin


class SecureConfig:
    """Production-ready secure configuration"""
    
    # Flask Core Security
    SECRET_KEY = os.environ.get('SESSION_SECRET', os.urandom(32).hex())
    DEBUG = os.environ.get('FLASK_ENV') != 'production'
    TESTING = False
    
    # Session Configuration (Redis-backed)
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'taskpages:session:'
    SESSION_COOKIE_NAME = 'taskpages_session'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in prod
    SESSION_COOKIE_DOMAIN = None  # Don't set domain - let browser handle it
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'None'  # Changed from 'Lax' to allow cross-site POST for token exchange
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # Auto-expire after 24 hours
    
    # Redis Configuration
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_MAX_CONNECTIONS = 10
    REDIS_SOCKET_TIMEOUT = 5
    REDIS_SOCKET_CONNECT_TIMEOUT = 5
    REDIS_RETRY_ON_TIMEOUT = True
    REDIS_HEALTH_CHECK_INTERVAL = 30
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    GOOGLE_WORKSPACE_DOMAIN = os.environ.get('GOOGLE_WORKSPACE_DOMAIN', 'oodahost.com')
    GOOGLE_DISCOVERY_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
    GOOGLE_CERTS_URL = 'https://www.googleapis.com/oauth2/v1/certs'
    
    # OAuth Security Settings
    OAUTH_STATE_LIFETIME = timedelta(minutes=10)  # State token expires in 10 minutes
    OAUTH_NONCE_LIFETIME = timedelta(minutes=10)  # Nonce expires in 10 minutes
    OAUTH_REQUIRE_WORKSPACE_DOMAIN = True  # Enforce workspace domain
    
    # URLs
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:5678')
    
    # CORS Configuration
    CORS_ORIGINS = [
        os.environ.get('FRONTEND_URL', 'http://localhost:3000'),
        'http://localhost:3000',
        'http://localhost:5678',
        'https://taskpages-frontend.onrender.com'
    ]
    CORS_SUPPORTS_CREDENTIALS = True
    CORS_METHODS = ['GET', 'POST', 'OPTIONS']
    CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization', 'X-CSRF-Token']
    CORS_MAX_AGE = 3600
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains; preload',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Content-Security-Policy': (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' " + os.environ.get('BACKEND_URL', 'http://localhost:5678') + "; "
            "frame-ancestors 'none';"
        )
    }
    
    # Rate Limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '100 per hour'
    RATELIMIT_LOGIN = '10 per hour'
    RATELIMIT_API = '1000 per hour'
    
    # Logging
    LOG_LEVEL = 'INFO' if os.environ.get('FLASK_ENV') == 'production' else 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ClickUp API (existing config)
    CLICKUP_API_TOKEN = os.environ.get('CLICKUP_API_TOKEN')
    CLICKUP_API_BASE_URL = 'https://api.clickup.com/api/v2'
    
    @staticmethod
    def is_safe_url(target):
        """Validate URL is safe for redirects"""
        if not target:
            return False
        ref_url = urlparse(SecureConfig.FRONTEND_URL)
        test_url = urlparse(urljoin(SecureConfig.FRONTEND_URL, target))
        return (test_url.scheme in ('http', 'https') and 
                ref_url.netloc == test_url.netloc)
    
    @staticmethod
    def get_redirect_uri():
        """Get the appropriate OAuth redirect URI"""
        if os.environ.get('FLASK_ENV') == 'production':
            return f"{SecureConfig.BACKEND_URL}/auth/callback"
        return "http://localhost:5678/auth/callback"
    
    @staticmethod
    def init_app(app):
        """Initialize app with security configuration"""
        app.config.from_object(SecureConfig)
        
        # Set additional security configs
        app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 if SecureConfig.DEBUG else 31536000
        
        return app