"""
Security Middleware for Flask Application
Implements security headers, rate limiting, and request validation
"""
import logging
import hashlib
import hmac
from functools import wraps
from datetime import datetime

from flask import request, jsonify, current_app, g
from werkzeug.exceptions import TooManyRequests
import redis

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Comprehensive security middleware for Flask applications
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security middleware with Flask app"""
        self.app = app
        
        # Register before/after request handlers
        app.before_request(self.before_request)
        app.after_request(self.after_request)
        
        # Register error handlers
        app.register_error_handler(403, self.handle_forbidden)
        app.register_error_handler(429, self.handle_rate_limit)
        
        logger.info("Security middleware initialized")
    
    def before_request(self):
        """
        Security checks before processing request
        """
        # Log request for audit trail
        g.request_id = hashlib.sha256(
            f"{request.remote_addr}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        
        logger.info(
            f"Request: {request.method} {request.path} "
            f"from {request.remote_addr} "
            f"[{g.request_id}]"
        )
        
        # Check for suspicious patterns
        if self._is_suspicious_request():
            logger.warning(f"Suspicious request blocked: {g.request_id}")
            return jsonify({'error': 'Invalid request'}), 400
        
        # Validate content type for POST/PUT requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.headers.get('Content-Type', '')
            if not any(ct in content_type for ct in ['application/json', 'multipart/form-data']):
                return jsonify({'error': 'Invalid content type'}), 400
        
        # Check request size
        if request.content_length and request.content_length > current_app.config.get('MAX_CONTENT_LENGTH', 16777216):
            return jsonify({'error': 'Request too large'}), 413
    
    def after_request(self, response):
        """
        Add security headers to response
        """
        # Add security headers from config
        for header, value in current_app.config.get('SECURITY_HEADERS', {}).items():
            response.headers[header] = value
        
        # Add request ID for tracing
        response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
        
        # Remove server header
        response.headers.pop('Server', None)
        
        # Add CORS headers if configured
        origin = request.headers.get('Origin')
        if origin in current_app.config.get('CORS_ORIGINS', []):
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            
            if request.method == 'OPTIONS':
                response.headers['Access-Control-Allow-Methods'] = ', '.join(
                    current_app.config.get('CORS_METHODS', ['GET', 'POST'])
                )
                response.headers['Access-Control-Allow-Headers'] = ', '.join(
                    current_app.config.get('CORS_ALLOW_HEADERS', ['Content-Type'])
                )
                response.headers['Access-Control-Max-Age'] = str(
                    current_app.config.get('CORS_MAX_AGE', 3600)
                )
        
        return response
    
    def _is_suspicious_request(self):
        """
        Check for suspicious request patterns
        """
        # Check for SQL injection patterns
        suspicious_patterns = [
            'union select',
            'drop table',
            '<script',
            'javascript:',
            '../',
            '..\\',
            '%00',
            '\x00',
            'base64,',
            'onerror=',
            'onclick='
        ]
        
        # Check URL parameters
        for key, value in request.args.items():
            value_lower = str(value).lower()
            if any(pattern in value_lower for pattern in suspicious_patterns):
                logger.warning(f"Suspicious pattern in URL param: {key}={value[:50]}")
                return True
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                value_lower = str(value).lower()
                if any(pattern in value_lower for pattern in suspicious_patterns):
                    logger.warning(f"Suspicious pattern in form data: {key}")
                    return True
        
        # Check User-Agent
        user_agent = request.headers.get('User-Agent', '').lower()
        suspicious_agents = ['sqlmap', 'nikto', 'nessus', 'metasploit', 'burp']
        if any(agent in user_agent for agent in suspicious_agents):
            logger.warning(f"Suspicious user agent: {user_agent}")
            return True
        
        return False
    
    def handle_forbidden(self, e):
        """Handle 403 Forbidden errors"""
        logger.warning(f"403 Forbidden: {request.url} from {request.remote_addr}")
        return jsonify({'error': 'Forbidden'}), 403
    
    def handle_rate_limit(self, e):
        """Handle 429 Rate Limit errors"""
        logger.warning(f"Rate limit exceeded: {request.remote_addr}")
        return jsonify({
            'error': 'Too many requests',
            'message': 'Please slow down your requests'
        }), 429


class RateLimiter:
    """
    Redis-based rate limiter
    """
    
    def __init__(self, redis_client, default_limit='100 per hour'):
        self.redis = redis_client
        self.default_limit = self._parse_limit(default_limit)
    
    def _parse_limit(self, limit_string):
        """Parse rate limit string like '100 per hour'"""
        parts = limit_string.split()
        count = int(parts[0])
        
        period_map = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }
        
        period = parts[2].rstrip('s')  # Remove plural 's'
        seconds = period_map.get(period, 3600)
        
        return count, seconds
    
    def check_rate_limit(self, key, limit=None):
        """
        Check if rate limit is exceeded
        Returns True if within limit, False if exceeded
        """
        if not limit:
            limit = self.default_limit
        else:
            limit = self._parse_limit(limit)
        
        count, period = limit
        
        # Create Redis key with expiration
        redis_key = f"rate_limit:{key}"
        
        try:
            # Use pipeline for atomic operation
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, period)
            results = pipe.execute()
            
            current_count = results[0]
            
            if current_count > count:
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open in case of Redis issues
            return True
    
    def rate_limit(self, limit=None, key_func=None):
        """
        Decorator for rate limiting routes
        """
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Determine rate limit key
                if key_func:
                    rate_key = key_func()
                else:
                    # Default: use IP address
                    rate_key = request.remote_addr
                
                # Check rate limit
                if not self.check_rate_limit(rate_key, limit):
                    raise TooManyRequests("Rate limit exceeded")
                
                return f(*args, **kwargs)
            
            return wrapped
        return decorator


def require_api_key(f):
    """
    Decorator to require API key for routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({'error': 'API key required'}), 401
        
        # Validate API key (implement your validation logic)
        expected_key = current_app.config.get('API_KEY')
        if not expected_key or not hmac.compare_digest(api_key, expected_key):
            logger.warning(f"Invalid API key from {request.remote_addr}")
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_json(*required_fields):
    """
    Decorator to validate JSON request body
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json()
            if not data:
                return jsonify({'error': 'Invalid JSON body'}), 400
            
            # Check required fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': 'Missing required fields',
                    'fields': missing_fields
                }), 400
            
            return f(*args, **kwargs)
        
        return wrapped
    return decorator