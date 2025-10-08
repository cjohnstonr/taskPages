# OAuth Redirect Fix - Implementation Summary

## Problem Resolved
Users accessing protected pages (like `/pages/task-helper`) while unauthenticated were redirected to the home page after OAuth login instead of being returned to their original page.

## Root Cause
The OAuth flow was using Referer headers to determine redirect URLs, but the Referer check only validated against `FRONTEND_URL`, not `BACKEND_URL`. Since protected pages are served from the backend domain, the Referer validation failed and users were sent to the home page.

## Solution Implemented
Implemented **OAuth 2.0 state parameter best practice** - storing the redirect URL securely in the OAuth state parameter instead of relying on Referer headers.

## Changes Made

### File: `/backend/auth/oauth_handler.py`

#### 1. Added New Imports
```python
import base64
from urllib.parse import urlparse  # Added to existing import
```

#### 2. Updated `/auth/login` Route (Lines 278-343)

**Before:** Used Referer header with `startswith()` validation (vulnerable to bypass)
**After:** Uses OAuth state parameter with:
- ✅ Base64-encoded state containing CSRF token + redirect URL
- ✅ Whitelist validation for allowed hosts
- ✅ Timestamp for expiration (10 minutes)
- ✅ No dependency on Referer headers

**Key Security Features:**
```python
# Whitelist validation
allowed_hosts = [
    urlparse(current_app.config['FRONTEND_URL']).netloc,
    urlparse(current_app.config['BACKEND_URL']).netloc,
    'localhost',
    '127.0.0.1'
]

# State payload with CSRF + redirect
state_data = {
    'csrf': csrf_token,
    'redirect': redirect_url,
    'timestamp': datetime.utcnow().isoformat()
}

# Base64 encode for Google OAuth roundtrip
state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
```

#### 3. Updated `/auth/callback` Route (Lines 346-479)

**Before:** Retrieved redirect from `session['next_url']` (could be overwritten)
**After:** Extracts redirect from validated OAuth state parameter

**Security Validations Added:**
1. ✅ Decode and parse state parameter
2. ✅ Verify CSRF token matches session (constant-time comparison)
3. ✅ Validate timestamp (10 minute expiry)
4. ✅ Whitelist check redirect URL
5. ✅ **Token in URL fragment (#) instead of query (?)** - prevents leakage

**Critical Security Fix:**
```python
# OLD (vulnerable to token leakage):
redirect_url = f"{next_url}?auth=success&token={auth_token}"

# NEW (secure - fragment never sent to servers):
final_redirect = f"{redirect_url}#auth=success&token={auth_token}"
```

## Security Improvements

### ✅ Fixed Vulnerabilities
1. **Open Redirect** - Whitelist validation prevents redirects to untrusted domains
2. **Token Leakage** - Fragment (#) prevents token exposure in Referer headers, server logs
3. **Session Race Conditions** - State parameter is immutable, can't be overwritten
4. **CSRF Attacks** - Cryptographic comparison of CSRF tokens
5. **Replay Attacks** - Timestamp validation, one-time nonce usage

### ✅ OAuth 2.0 Best Practices Followed
- Uses state parameter for redirect tracking (official OAuth 2.0 pattern)
- Base64 encoding ensures data roundtrips unchanged through Google
- CSRF token in state + session for dual validation
- Time-limited state (10 minute expiry)
- Secure token delivery via URL fragment

## Impact on Existing Pages

### ✅ No Breaking Changes
All existing authenticated pages continue to work **exactly as before**:
- `/pages/wait-node`
- `/pages/wait-node-v2`
- `/pages/wait-node-editable`
- `/pages/task-helper`

**Why?** All pages use `credentials: 'include'` for session cookie authentication, not the token in the URL.

## Testing Checklist

### Basic Functionality
- [ ] Visit `/pages/task-helper` while unauthenticated
- [ ] Complete OAuth flow
- [ ] Verify redirect back to `/pages/task-helper` (not home page)
- [ ] Confirm session works (can access API endpoints)

### Other Protected Pages
- [ ] Test `/pages/wait-node` - should redirect to same page after auth
- [ ] Test `/pages/wait-node-v2` - should redirect to same page after auth
- [ ] Test `/pages/wait-node-editable` - should redirect to same page after auth

### Security Validation
- [ ] Check browser network tab - token should NOT appear in Referer header
- [ ] Verify token is in URL fragment (#) not query (?)
- [ ] Confirm whitelist blocks untrusted domains
- [ ] Test state expiration (wait >10 minutes, should fail)

## Deployment Notes

1. **No environment variable changes required** - Uses existing config
2. **No frontend changes required** - Pages use session cookies
3. **Backward compatible** - Existing OAuth flow still works
4. **Redis optional** - Falls back to session storage if Redis unavailable

## Monitoring

Watch for these log messages after deployment:
- `"OAuth login initiated from IP"` - Should show redirect URL in state
- `"Redirecting to: {url} (token in fragment)"` - Confirms fragment usage
- `"Rejecting redirect to untrusted host"` - Security whitelist working
- `"CSRF token mismatch"` - Potential attack attempt

## References
- OAuth 2.0 State Parameter: https://auth0.com/docs/secure/attack-protection/state-parameters
- Google OAuth Best Practices: https://developers.google.com/identity/protocols/oauth2/web-server
- URL Fragment Security: OAuth 2.0 RFC 6749 (Implicit Flow discussion)
