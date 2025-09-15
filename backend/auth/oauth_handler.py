"""
Google OAuth 2.0 Authentication Handler
Implements secure OAuth flow with CSRF protection and domain validation
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlencode, quote

import requests
from flask import (
    Blueprint, 
    request, 
    redirect, 
    session, 
    jsonify, 
    abort,
    current_app,
    url_for
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import redis
import json

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Redis client (will be initialized by app)
redis_client = None


def init_redis(app):
    """Initialize Redis connection with security settings"""
    global redis_client
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Log the Redis URL we're trying to connect to (without exposing credentials)
    logger.info(f"Attempting Redis connection to: {redis_url.split('@')[-1] if '@' in redis_url else redis_url.split('//')[-1]}")
    
    try:
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_keepalive=True,
            socket_keepalive_options={
                1: 1,  # TCP_KEEPIDLE
                2: 1,  # TCP_KEEPINTVL
                3: 3,  # TCP_KEEPCNT
            },
            socket_connect_timeout=5,
            retry_on_timeout=True,
            max_connections=10,
            health_check_interval=30
        )
    except Exception as e:
        logger.warning(f"Failed with keepalive options: {e}, trying simpler connection")
        # Fallback to simpler connection for compatibility
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            max_connections=10
        )
    
    # Test connection
    try:
        redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise
    
    return redis_client


def generate_csrf_token():
    """Generate a secure CSRF token"""
    token = secrets.token_urlsafe(32)
    return token


def verify_csrf_token(token):
    """Verify CSRF token from session"""
    stored_token = session.pop('oauth_state', None)
    if not stored_token or not token:
        return False
    return secrets.compare_digest(stored_token, token)


def verify_google_token(token_string):
    """
    Verify Google ID token with comprehensive security checks
    """
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token_string,
            google_requests.Request(),
            current_app.config['GOOGLE_CLIENT_ID'],
            clock_skew_in_seconds=10  # Allow 10 seconds clock skew
        )
        
        # Verify token is from Google
        if idinfo.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            logger.warning(f"Invalid issuer: {idinfo.get('iss')}")
            return None
        
        # Verify audience
        if idinfo.get('aud') != current_app.config['GOOGLE_CLIENT_ID']:
            logger.warning(f"Invalid audience: {idinfo.get('aud')}")
            return None
        
        # Verify workspace domain if required
        if current_app.config.get('OAUTH_REQUIRE_WORKSPACE_DOMAIN', True):
            workspace_domain = current_app.config['GOOGLE_WORKSPACE_DOMAIN']
            
            # Check HD (hosted domain) claim
            if idinfo.get('hd') != workspace_domain:
                logger.warning(f"Invalid hosted domain: {idinfo.get('hd')} != {workspace_domain}")
                return None
            
            # Double-check email domain
            email = idinfo.get('email', '')
            if not email.endswith(f'@{workspace_domain}'):
                logger.warning(f"Invalid email domain: {email}")
                return None
        
        # Verify email is verified
        if not idinfo.get('email_verified'):
            logger.warning(f"Email not verified for: {idinfo.get('email')}")
            return None
        
        return idinfo
    
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        return None


def create_user_session(user_info):
    """
    Create a secure user session in Redis
    """
    # Generate session ID
    session_id = secrets.token_urlsafe(32)
    
    # Prepare session data
    session_data = {
        'user_id': user_info.get('sub'),  # Google's unique user ID
        'email': user_info.get('email'),
        'name': user_info.get('name'),
        'picture': user_info.get('picture'),
        'workspace_domain': user_info.get('hd'),
        'created_at': datetime.utcnow().isoformat(),
        'last_activity': datetime.utcnow().isoformat(),
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', '')[:200]  # Limit length
    }
    
    # Store in Redis with expiration
    session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
    expiry = int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
    
    # Use pipeline for atomic operations
    pipe = redis_client.pipeline()
    pipe.setex(session_key, expiry, json.dumps(session_data))
    
    # Track user's sessions (for logout everywhere functionality)
    user_sessions_key = f"user_sessions:{user_info.get('email')}"
    pipe.sadd(user_sessions_key, session_id)
    pipe.expire(user_sessions_key, expiry)
    
    pipe.execute()
    
    # Set session cookie
    session['session_id'] = session_id
    session['user_email'] = user_info.get('email')
    session.permanent = False  # Use session cookie, not permanent
    
    logger.info(f"Session created for user: {user_info.get('email')}")
    
    return session_id


def get_user_session():
    """
    Retrieve and validate user session from Redis
    """
    session_id = session.get('session_id')
    if not session_id:
        return None
    
    session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
    session_data = redis_client.get(session_key)
    
    if not session_data:
        # Session expired or doesn't exist
        session.clear()
        return None
    
    try:
        user_data = json.loads(session_data)
        
        # Update last activity
        user_data['last_activity'] = datetime.utcnow().isoformat()
        expiry = int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
        redis_client.setex(session_key, expiry, json.dumps(user_data))
        
        return user_data
    except Exception as e:
        logger.error(f"Failed to parse session data: {e}")
        session.clear()
        return None


def login_required(f):
    """
    Decorator to require authentication for routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_session = get_user_session()
        if not user_session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Store the URL the user was trying to access
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        
        # Add user info to request context
        request.user = user_session
        return f(*args, **kwargs)
    
    return decorated_function


@auth_bp.route('/login')
def login():
    """
    Initiate OAuth login flow with CSRF protection
    """
    # Generate CSRF state token
    state = generate_csrf_token()
    session['oauth_state'] = state
    session['oauth_timestamp'] = datetime.utcnow().isoformat()
    
    # Generate nonce for additional security
    nonce = secrets.token_urlsafe(32)
    session['oauth_nonce'] = nonce
    
    # Build OAuth URL
    params = {
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri': current_app.config.get_redirect_uri(),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'nonce': nonce,
        'access_type': 'online',  # Don't need offline access
        'prompt': 'select_account',  # Always show account selector
    }
    
    # Add hosted domain hint for workspace
    if current_app.config.get('OAUTH_REQUIRE_WORKSPACE_DOMAIN'):
        params['hd'] = current_app.config['GOOGLE_WORKSPACE_DOMAIN']
    
    oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    
    logger.info(f"Initiating OAuth login from IP: {request.remote_addr}")
    
    return redirect(oauth_url)


@auth_bp.route('/callback')
def callback():
    """
    Handle OAuth callback with comprehensive security checks
    """
    # Check for errors from Google
    error = request.args.get('error')
    if error:
        logger.error(f"OAuth error: {error}")
        return jsonify({'error': f'Authentication failed: {error}'}), 400
    
    # Verify CSRF state token
    state = request.args.get('state')
    if not verify_csrf_token(state):
        logger.warning(f"CSRF token verification failed from IP: {request.remote_addr}")
        abort(403, "Invalid state parameter - possible CSRF attack")
    
    # Check timestamp to prevent replay attacks
    oauth_timestamp = session.pop('oauth_timestamp', None)
    if oauth_timestamp:
        time_diff = datetime.utcnow() - datetime.fromisoformat(oauth_timestamp)
        if time_diff > timedelta(minutes=10):
            logger.warning("OAuth callback took too long - possible replay attack")
            abort(403, "Authentication timeout - please try again")
    
    # Get authorization code
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'No authorization code received'}), 400
    
    # Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'client_secret': current_app.config['GOOGLE_CLIENT_SECRET'],
        'redirect_uri': current_app.config.get_redirect_uri(),
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_response.raise_for_status()
        tokens = token_response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Token exchange failed: {e}")
        return jsonify({'error': 'Failed to exchange authorization code'}), 500
    
    # Verify ID token
    id_token_str = tokens.get('id_token')
    if not id_token_str:
        return jsonify({'error': 'No ID token received'}), 400
    
    user_info = verify_google_token(id_token_str)
    if not user_info:
        return jsonify({'error': 'Invalid ID token'}), 403
    
    # Verify nonce
    expected_nonce = session.pop('oauth_nonce', None)
    if not expected_nonce or user_info.get('nonce') != expected_nonce:
        logger.warning("Nonce verification failed")
        abort(403, "Invalid nonce - possible replay attack")
    
    # Create user session
    session_id = create_user_session(user_info)
    
    # Determine redirect URL
    next_url = session.pop('next_url', None)
    if next_url and current_app.config.is_safe_url(next_url):
        redirect_url = next_url
    else:
        # Redirect to frontend with success indicator
        redirect_url = f"{current_app.config['FRONTEND_URL']}?auth=success"
    
    logger.info(f"Successful login for: {user_info.get('email')}")
    
    return redirect(redirect_url)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user and clear session
    """
    session_id = session.get('session_id')
    user_email = session.get('user_email')
    
    if session_id:
        # Remove session from Redis
        session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
        redis_client.delete(session_key)
        
        # Remove from user's session set
        if user_email:
            user_sessions_key = f"user_sessions:{user_email}"
            redis_client.srem(user_sessions_key, session_id)
        
        logger.info(f"User logged out: {user_email}")
    
    # Clear Flask session
    session.clear()
    
    return jsonify({'message': 'Logged out successfully'}), 200


@auth_bp.route('/logout-all', methods=['POST'])
@login_required
def logout_all():
    """
    Logout user from all devices
    """
    user_email = request.user.get('email')
    
    # Get all user sessions
    user_sessions_key = f"user_sessions:{user_email}"
    all_sessions = redis_client.smembers(user_sessions_key)
    
    # Delete all sessions
    pipe = redis_client.pipeline()
    for sid in all_sessions:
        session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{sid}"
        pipe.delete(session_key)
    pipe.delete(user_sessions_key)
    pipe.execute()
    
    # Clear current session
    session.clear()
    
    logger.info(f"All sessions cleared for user: {user_email}")
    
    return jsonify({'message': 'Logged out from all devices'}), 200


@auth_bp.route('/status')
def auth_status():
    """
    Check authentication status
    """
    user_session = get_user_session()
    
    if user_session:
        return jsonify({
            'authenticated': True,
            'user': {
                'email': user_session.get('email'),
                'name': user_session.get('name'),
                'picture': user_session.get('picture')
            }
        }), 200
    
    return jsonify({'authenticated': False}), 200


@auth_bp.route('/refresh', methods=['POST'])
@login_required
def refresh_session():
    """
    Refresh session expiration
    """
    # Session is automatically refreshed in get_user_session()
    return jsonify({'message': 'Session refreshed'}), 200