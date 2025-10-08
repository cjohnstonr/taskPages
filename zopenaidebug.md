# OpenAI Integration Debug Documentation

## Current Issue
The Task Helper page's "Generate AI Summary" button returns a 500 Internal Server Error when clicked.

## OpenAI Integration Flow

### 1. Frontend Call Chain

#### Location: `/backend/templates/secured/task-helper.html`

##### Trigger Point (Line 489)
```javascript
<button onClick={generateSummary}>
    {isGenerating ? 'Generating...' : '🤖 Generate AI Summary'}
</button>
```

##### Main Function: `generateSummary` (Lines 252-303)
```javascript
const generateSummary = async () => {
    // Line 260: API Call
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
    
    // Lines 276-296: Response Handling
    if (response.ok) {
        setAiSummary(data.summary);
    } else {
        // Tries to extract fallback summary from error response
        const errorData = await response.json();
        if (errorData.summary) {
            setAiSummary(errorData.summary);
        }
    }
}
```

##### State Management
- Line 229: `const [aiSummary, setAiSummary] = useState('');`
- Line 232: `const [isGenerating, setIsGenerating] = useState(false);`
- Lines 278, 289, 299: Sets AI summary in state
- Lines 496-500: Displays AI summary in UI

### 2. Backend Endpoint Chain

#### Location: `/backend/app_secure.py`

##### Route Definition (Lines 965-968)
```python
@app.route('/api/ai/generate-escalation-summary', methods=['POST'])
@login_required  
@rate_limiter.rate_limit(limit='20 per minute')
def generate_escalation_summary():
```

##### OpenAI Configuration (Lines 33-40)
```python
# Line 13: Import
import openai

# Lines 34-36: Configuration
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.warning("OpenAI API key not found in environment variables")
```

##### API Call Implementation (Lines 1021-1096)

###### Primary Try: GPT-3.5-turbo (Lines 1027-1039)
```python
try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Changed from gpt-4
        messages=[
            {"role": "system", "content": "..."},
            {"role": "user", "content": ai_prompt}
        ],
        max_tokens=400,
        temperature=0.7
    )
    ai_summary = response.choices[0].message.content.strip()
    model_used = "gpt-3.5-turbo"
```

###### Fallback 1: GPT-4 (Lines 1041-1054)
```python
except Exception as e:
    logger.warning(f"GPT-3.5-turbo failed, trying GPT-4: {e}")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        # Same parameters
    )
    model_used = "gpt-4"
```

###### Fallback 2: Structured Summary (Lines 1065-1096)
```python
except Exception as openai_error:
    logger.error(f"OpenAI API error: {openai_error}")
    
    # Creates structured fallback summary
    fallback_summary = f"""**ESCALATION SUMMARY**
    **Task**: {task_info.get('name', 'Unknown Task')} ({task_id})
    ...
    """
    
    return jsonify({
        "summary": fallback_summary,
        "model_used": "fallback",
        "ai_error": str(openai_error)
    })
```

###### Emergency Fallback (Lines 1098-1117)
```python
except Exception as e:
    # Final emergency fallback
    emergency_summary = f"Task {task_id} requires escalation: {reason[:100]}..."
    return jsonify({
        "summary": emergency_summary,
        "model_used": "emergency_fallback"
    })
```

## API Key Location
- **File**: `/backend/.env`
- **Key**: `OPENAI_API_KEY=sk-proj-SOlkJ3ivUI_QEvdO1QgF1rzC55iEv3MtuaqISFH00gaIJ1kl4zGaiWoMS...`

## Dependencies
- **Backend**: `openai==0.28.1` (specified in requirements.txt)
- **Critical**: Must use v0.28.1 syntax, NOT v1.x syntax

## Known Issues & Fixes Applied

### Issue 1: Version Mismatch
- **Problem**: Local had openai v1.107.0, backend expects v0.28.1
- **Solution**: Code uses v0.28.1 syntax (`openai.ChatCompletion.create`)

### Issue 2: GPT-4 Access
- **Problem**: API key might not have GPT-4 access
- **Solution**: Changed primary model to GPT-3.5-turbo (line 1029)

### Issue 3: No Complete Failure
- **Problem**: Endpoint could return 500 with no summary
- **Solution**: Multi-tier fallback system ensures always returns a summary

## Fallback Hierarchy
1. **Primary**: GPT-3.5-turbo with OpenAI
2. **Secondary**: GPT-4 with OpenAI
3. **Tertiary**: Structured template summary
4. **Emergency**: Basic one-line summary

## Testing Files
1. `/test_openai.py` - Basic OpenAI test with v0.28.1 syntax
2. `/test_openai_v0.py` - Comprehensive test mimicking backend flow
3. `/test_task_helper.py` - Tests endpoint connectivity

## Final Diagnosis After Testing

The OpenAI integration was failing due to MULTIPLE compounding issues:

1. **Version Detection Bug**: `hasattr(openai, 'ChatCompletion')` returns True even in v1.0+ (it exists to throw an error!)
2. **httpx Incompatibility**: OpenAI v1.3.0 tries to pass 'proxies' to httpx.Client, but httpx v0.28.1 doesn't support it
3. **AttributeError**: `request.user.get('email')` doesn't exist in Flask
4. **No Proper Error Handling**: Failures weren't logged properly

## Root Causes Identified

### 1. Critical Bug: request.user AttributeError
**Line 1072 (FIXED)**: `request.user.get('email')` - Flask request objects don't have a `user` attribute
- This was causing an AttributeError that made the entire endpoint fail with 500
- **Fix Applied**: Changed to `session.get('user', {}).get('email', 'Unknown')`

### 2. Wrong Model Priority
**Line 1029 (FIXED)**: Was using GPT-3.5-turbo as primary model
- **Fix Applied**: Changed to GPT-4 as primary, GPT-4-turbo-preview as fallback

### 3. Mock Data in Responses
**Lines 1068-1103 (FIXED)**: Fallback was returning mock/template summaries
- **Fix Applied**: Removed all fallback summaries, now returns proper error responses

## Current Status After All Fixes

### Comprehensive Solution Implemented
The backend now handles ALL version scenarios:

1. **Proper Version Detection**: Checks `openai.__version__` and parses major version
2. **Multiple Syntax Support**:
   - v0.28.x: Uses `openai.ChatCompletion.create()`  
   - v1.0+: Uses `client.chat.completions.create()`
3. **httpx Compatibility Handling**: Catches TypeError and falls back to old syntax
4. **Emergency Fallback**: If v1.0+ fails completely, tries old syntax anyway
5. **Extensive Logging**: Every step logged with [AI SUMMARY] prefix

### Error Response Changes
- No more mock/fallback summaries
- Returns 503 with technical error details
- Frontend shows full error with technical details

## Changes Applied (Both Commits)
1. Fixed `request.user` bug → `session.get('user', {})`
2. Changed model from GPT-3.5-turbo → GPT-4
3. Fixed version detection to check `__version__` not `ChatCompletion`
4. Added httpx compatibility error handling
5. Added emergency fallback between syntax versions
6. Removed ALL mock/fallback summaries
7. Added comprehensive logging at every step
8. Updated frontend error handling to show technical details

## Debug Steps
1. Check Render logs for specific OpenAI error
2. Verify API key is valid and has quota
3. Test with local script using exact backend code
4. Confirm openai==0.28.1 is installed on Render

## Response Format
```json
{
    "success": true,
    "summary": "Generated or fallback summary text",
    "generated_at": "ISO timestamp",
    "task_id": "task_id",
    "model_used": "gpt-3.5-turbo|gpt-4|fallback|emergency_fallback",
    "ai_error": "Error message if using fallback"
}
```