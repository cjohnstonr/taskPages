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
import hashlib
import hmac

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
    
    # Check if Redis is disabled
    if os.environ.get('DISABLE_REDIS', 'false').lower() == 'true':
        logger.warning("Redis disabled - sessions will not persist across restarts")
        redis_client = None
        return None
    
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
    Create a secure user session (Redis or Flask session)
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
    
    if redis_client:
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
    else:
        # Fallback to Flask session
        session['user_data'] = session_data
    
    # Set session cookie
    session['session_id'] = session_id
    session['user_email'] = user_info.get('email')
    session.permanent = False  # Use session cookie, not permanent
    
    logger.info(f"Session created for user: {user_info.get('email')} (Redis: {redis_client is not None})")
    
    return session_id


def get_user_session():
    """
    Retrieve and validate user session (Redis or Flask session)
    """
    session_id = session.get('session_id')
    if not session_id:
        return None
    
    if redis_client:
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
    else:
        # Fallback to Flask session
        user_data = session.get('user_data')
        if user_data:
            # Update last activity
            user_data['last_activity'] = datetime.utcnow().isoformat()
            session['user_data'] = user_data
        return user_data


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
    # Store the referring page for post-OAuth redirect
    referrer = request.headers.get('Referer')
    if referrer and referrer.startswith(current_app.config['FRONTEND_URL']):
        session['next_url'] = referrer
        logger.info(f"Storing referrer for post-OAuth redirect: {referrer}")
    
    # Generate CSRF state token
    state = generate_csrf_token()
    session['oauth_state'] = state
    session['oauth_timestamp'] = datetime.utcnow().isoformat()
    
    # Ensure session is properly saved
    session.modified = True
    
    # Generate nonce for additional security
    nonce = secrets.token_urlsafe(32)
    session['oauth_nonce'] = nonce
    
    # Ensure session modifications are saved
    session.modified = True
    
    # DEBUG: Log what we're storing
    logger.info(f"OAuth login initiated. Session ID: {session.get('session_id', 'None')}")
    logger.info(f"Storing state: {state}")
    logger.info(f"Session keys after storage: {list(session.keys())}")
    logger.info(f"Session permanent: {session.permanent}")
    
    # Build OAuth URL
    params = {
        'client_id': current_app.config['GOOGLE_CLIENT_ID'],
        'redirect_uri': f"{current_app.config['BACKEND_URL']}/auth/callback",
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
    # DEBUG: Log session state at callback entry
    logger.info(f"OAuth callback received. Session ID: {session.get('session_id', 'None')}")
    logger.info(f"Session keys: {list(session.keys())}")
    logger.info(f"OAuth state in session: {session.get('oauth_state', 'None')}")
    logger.info(f"Request args: {dict(request.args)}")
    
    # Check for errors from Google
    error = request.args.get('error')
    if error:
        logger.error(f"OAuth error: {error}")
        return jsonify({'error': f'Authentication failed: {error}'}), 400
    
    # Verify CSRF state token
    state = request.args.get('state')
    stored_state = session.get('oauth_state')
    logger.info(f"State verification: received='{state}', stored='{stored_state}'")
    
    if not verify_csrf_token(state):
        logger.warning(f"CSRF token verification failed from IP: {request.remote_addr}")
        logger.warning(f"State mismatch: received='{state}', stored='{stored_state}'")
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
        'redirect_uri': f"{current_app.config['BACKEND_URL']}/auth/callback",
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
    
    # Generate a secure authentication token for cross-domain use
    auth_token = secrets.token_urlsafe(32)
    
    # Store token in Redis or session for validation
    if redis_client:
        token_key = f"auth_token:{auth_token}"
        token_data = {
            'session_id': session_id,
            'email': user_info.get('email'),
            'created_at': datetime.utcnow().isoformat()
        }
        # Token expires in 5 minutes - enough time for frontend to exchange it
        redis_client.setex(token_key, 300, json.dumps(token_data))
    else:
        # Fallback: store in session
        session[f'auth_token_{auth_token}'] = {
            'session_id': session_id,
            'email': user_info.get('email'),
            'created_at': datetime.utcnow().isoformat()
        }
    
    # Determine redirect URL
    next_url = session.pop('next_url', None)
    # Simple URL safety check
    if next_url and next_url.startswith(('/', current_app.config['FRONTEND_URL'])):
        redirect_url = f"{next_url}?auth=success&token={auth_token}"
    else:
        # Redirect to frontend with success indicator and token
        redirect_url = f"{current_app.config['FRONTEND_URL']}?auth=success&token={auth_token}"
    
    logger.info(f"Successful login for: {user_info.get('email')}")
    logger.info(f"Created auth token for cross-domain use")
    logger.info(f"Redirecting to: {redirect_url.split('&token=')[0] + '&token=***'}")
    
    return redirect(redirect_url)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user and clear session
    """
    session_id = session.get('session_id')
    user_email = session.get('user_email')
    
    if session_id and redis_client:
        # Remove session from Redis
        session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
        redis_client.delete(session_key)
        
        # Remove from user's session set
        if user_email:
            user_sessions_key = f"user_sessions:{user_email}"
            redis_client.srem(user_sessions_key, session_id)
    
    if user_email:
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
    
    if redis_client:
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
    # Check for token in Authorization header for cross-domain requests
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.replace('Bearer ', '')
        # Try API token first (long-lived token)
        user_session = validate_api_token(token)
        if not user_session:
            # Try temporary auth token
            user_session = validate_auth_token(token)
        
        if user_session:
            return jsonify({
                'authenticated': True,
                'user': {
                    'email': user_session.get('email'),
                    'name': user_session.get('name'),
                    'picture': user_session.get('picture')
                }
            }), 200
    
    # Fallback to cookie-based session
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


def validate_auth_token(token):
    """
    Validate an authentication token and return session data
    """
    if not token:
        return None
    
    if redis_client:
        token_key = f"auth_token:{token}"
        token_data = redis_client.get(token_key)
        if not token_data:
            return None
        
        try:
            data = json.loads(token_data)
            session_id = data.get('session_id')
            
            # Get the actual session data
            session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
            session_data = redis_client.get(session_key)
            
            if session_data:
                return json.loads(session_data)
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return None
    else:
        # Fallback to session-based validation
        token_data = session.get(f'auth_token_{token}')
        if token_data:
            session_id = token_data.get('session_id')
            # Return the user data from session
            return session.get('user_data')
    
    return None


@auth_bp.route('/exchange-token', methods=['POST'])
def exchange_token():
    """
    Exchange a temporary auth token for a long-lived session token
    """
    data = request.json
    temp_token = data.get('token')
    
    if not temp_token:
        return jsonify({'error': 'No token provided'}), 400
    
    # Validate the temporary token
    if redis_client:
        token_key = f"auth_token:{temp_token}"
        token_data = redis_client.get(token_key)
        
        if not token_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        try:
            data = json.loads(token_data)
            session_id = data.get('session_id')
            
            # Get the actual session data
            session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
            session_data = redis_client.get(session_key)
            
            if not session_data:
                return jsonify({'error': 'Session not found'}), 401
            
            user_data = json.loads(session_data)
            
            # Create a long-lived API token
            api_token = secrets.token_urlsafe(32)
            api_token_key = f"api_token:{api_token}"
            
            # Store API token with longer expiry (24 hours)
            expiry = int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
            redis_client.setex(api_token_key, expiry, json.dumps({
                'session_id': session_id,
                'email': user_data.get('email'),
                'created_at': datetime.utcnow().isoformat()
            }))
            
            # Delete the temporary token
            redis_client.delete(token_key)
            
            return jsonify({
                'success': True,
                'api_token': api_token,
                'user': {
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'picture': user_data.get('picture')
                }
            }), 200
            
        except Exception as e:
            logger.error(f"Error exchanging token: {e}")
            return jsonify({'error': 'Token exchange failed'}), 500
    else:
        # Fallback for non-Redis setup
        token_data = session.pop(f'auth_token_{temp_token}', None)
        if not token_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user_data = session.get('user_data')
        if not user_data:
            return jsonify({'error': 'Session not found'}), 401
        
        # In non-Redis mode, return the session data directly
        # The session cookie will maintain the auth
        return jsonify({
            'success': True,
            'api_token': temp_token,  # Reuse the token in non-Redis mode
            'user': {
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture')
            }
        }), 200


def validate_api_token(token):
    """
    Validate a long-lived API token and return session data
    """
    if not token:
        return None
    
    if redis_client:
        api_token_key = f"api_token:{token}"
        token_data = redis_client.get(api_token_key)
        
        if not token_data:
            return None
        
        try:
            data = json.loads(token_data)
            session_id = data.get('session_id')
            
            # Get the actual session data
            session_key = f"{current_app.config['SESSION_KEY_PREFIX']}{session_id}"
            session_data = redis_client.get(session_key)
            
            if session_data:
                # Refresh token expiry on each use
                expiry = int(current_app.config['PERMANENT_SESSION_LIFETIME'].total_seconds())
                redis_client.expire(api_token_key, expiry)
                return json.loads(session_data)
        except Exception as e:
            logger.error(f"Error validating API token: {e}")
            return None
    
    return None