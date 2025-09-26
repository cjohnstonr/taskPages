# Critical Bug Investigation Context

## Project Overview
**Project**: Task Pages - Task Helper Module  
**Repository**: https://github.com/cjohnstonr/taskPages  
**Live Backend**: https://taskpages-backend.onrender.com  
**Deployment Platform**: Render  

## Current Critical Issue
The AI summary generation feature is failing with a `'NoneType' object has no attribute 'get'` error when users click the "Generate AI Summary" button.

## Error Details
```
Technical details: 'NoneType' object has no attribute 'get'
HTTP Status: 500 Internal Server Error
Endpoint: POST /api/ai/generate-escalation-summary
```

## File Structure

### Frontend File
**Path**: `/backend/templates/secured/task-helper.html`
- React-based single-page application
- Uses Babel for JSX transformation inline
- Key Function: `generateSummary` (Lines 252-303)
- API Call: Line 260
```javascript
const response = await fetch(`${BACKEND_URL}/api/ai/generate-escalation-summary`, {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        task_id: task.id,
        reason: escalationText,
        context: {
            task: task,
            parent_task: parentTask
        }
    })
});
```

### Backend File
**Path**: `/backend/app_secure.py`
- Flask application with session-based authentication
- Route: `/api/ai/generate-escalation-summary` (Lines 965-1135)
- OpenAI integration with version compatibility handling

## What We've Already Tried (AND FAILED)

### Attempt 1: Fixed `request.user` AttributeError
- **Problem**: `request.user.get('email')` doesn't exist in Flask
- **Fix Applied**: Changed ALL 16 instances to `session.get('user', {}).get('email', 'Unknown')`
- **Result**: STILL FAILING with same error

### Attempt 2: Fixed Logger Initialization Order
- **Problem**: Logger used before definition (line 36 vs 47)
- **Fix Applied**: Moved logger initialization to top
- **Result**: Deploy succeeded but error persists

### Attempt 3: OpenAI Version Compatibility
- **Problem**: OpenAI v1.0+ has different syntax than v0.28
- **Fix Applied**: Added version detection and dual syntax support
- **Result**: Error still occurs

### Attempt 4: Added OpenAI API Key to Render
- **Problem**: Environment variable wasn't set
- **Fix Applied**: Added OPENAI_API_KEY to Render environment
- **Result**: Key is now available but error persists

## Environment Details

### Backend Dependencies (requirements.txt)
- Flask==3.0.3
- openai==0.28.1
- python-dotenv==1.0.0
- requests==2.31.0
- redis==5.0.1
- flask-session==0.6.0
- flask-cors==4.0.0
- gunicorn==21.2.0

### Render Deployment
- Python version: 3.13.4 (based on error logs)
- Service ID: srv-d346q7q4d50c73eq60qg
- Latest Deploy: Live as of 2025-09-26T06:53:29Z

## The Persistent Error

Despite all fixes, the error persists:
```python
2025-09-26 06:56:23,329 - app_secure - ERROR - Error generating AI summary: 'NoneType' object has no attribute 'get'
```

This error is caught by the outer try/except block starting at line 1131 in app_secure.py:
```python
except Exception as e:
    logger.error(f"Error generating AI summary: {e}")
    # Return error - no mock data
    return jsonify({
        "success": False,
        "error": "Failed to generate AI summary. Please try again later.",
        "technical_error": str(e)
    }), 500
```

## YOUR INVESTIGATION TASK

1. **The error is happening BEFORE the OpenAI call** - it's in the setup/preparation code
2. **Line numbers to focus on**: 973-1020 (before OpenAI is actually called)
3. **The `.get()` method is being called on something that is None**
4. **Session data might be structured differently than expected**

## Specific Areas to Investigate

1. **Session Structure**: 
   - Is `session.get('user', {})` actually returning a dictionary?
   - Could `session.get('user', {})` be returning None instead of {}?

2. **Request Data Structure**:
   - Lines 977-979: Are these `.get()` calls working?
   - Could `data` be None even after the check on line 974?

3. **Context Object**:
   - Lines 988-993: Multiple `.get()` calls on context data
   - Could any of these be None?

4. **Hidden `.get()` Calls**:
   - Are there any `.get()` calls in imported modules or decorators?
   - Check the `@login_required` decorator
   - Check the `@rate_limiter.rate_limit()` decorator

## Request Payload from Frontend
```json
{
    "task_id": "868fgqn08",
    "reason": "Task needs escalation text here",
    "context": {
        "task": {/* task object */},
        "parent_task": {/* parent task object or null */}
    }
}
```

## Critical Questions

1. WHERE EXACTLY is the NoneType error occurring? We need the exact line number.
2. WHAT object is None that shouldn't be?
3. WHY would it be None in production but potentially work locally?
4. Is there a difference in how sessions are handled on Render vs local?

## Debug Strategy Needed

We need to add debug logging at EVERY `.get()` call to identify which one is failing. The error message doesn't give us the line number, which is critical.

## Files to Review
1. `/backend/app_secure.py` - Lines 965-1135 (the endpoint)
2. `/backend/auth/oauth_handler.py` - The `login_required` decorator
3. `/backend/auth/security_middleware.py` - The rate limiter
4. The session configuration and Redis setup

## The Ask
Find the EXACT line where `.get()` is being called on None. Add comprehensive debug logging if needed. This error has persisted through multiple "fixes" which means we're not identifying the actual problem correctly.