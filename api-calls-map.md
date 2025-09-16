# API Calls Map - wait-node.html

## Summary of Findings

After a comprehensive analysis of `/Users/AIRBNB/Task-Specific-Pages/wait-node.html`, I identified **12 API calls** across the application:

- **Backend Python API calls**: 8 calls
- **Supabase Edge Function calls**: 4 calls
- **Other**: 0 calls

## Detailed API Calls Table

| Line | Code Snippet | API Type | Endpoint | Purpose | Authentication |
|------|--------------|----------|----------|---------|----------------|
| 215 | `await fetch(\`${BACKEND_URL}/api${endpoint}\`, {...})` | Backend Python | Dynamic endpoint via `makeApiRequest()` | Generic API request wrapper function | ✅ Bearer token |
| 246 | `await makeApiRequest(\`/task/${startTaskId}?custom_task_ids=true\`)` | Backend Python | `/task/{id}?custom_task_ids=true` | Fetch task details for finding Process Library root | ✅ Bearer token |
| 258 | `await makeApiRequest(\`/task/${currentTask.parent}?custom_task_ids=true\`)` | Backend Python | `/task/{id}?custom_task_ids=true` | Fetch parent task details while traversing hierarchy | ✅ Bearer token |
| 278 | `await makeApiRequest(\`/task/${parentTaskId}?include_subtasks=true\`)` | Backend Python | `/task/{id}?include_subtasks=true` | Fetch parent task with subtasks list | ✅ Bearer token |
| 290 | `await makeApiRequest(\`/task/${subtask.id}?custom_task_ids=true\`)` | Backend Python | `/task/{id}?custom_task_ids=true` | Fetch individual subtask details with custom fields | ✅ Bearer token |
| 568 | `await fetch(EDGE_FUNCTION_URL, {...})` | Supabase Edge Function | `EDGE_FUNCTION_URL` (undefined variable) | Update custom field via edge function | ❌ No auth headers |
| 631 | `await makeApiRequest(\`/task/${taskData.id}?custom_task_ids=true\`)` | Backend Python | `/task/{id}?custom_task_ids=true` | Verify task update after approval submission | ✅ Bearer token |
| 863 | `await findProcessLibraryRoot(taskId)` | Backend Python | Indirect - calls `/task/{id}?custom_task_ids=true` | Find root Process Library task | ✅ Bearer token |
| 871 | `await makeApiRequest(\`/task/${taskId}?custom_task_ids=true\`)` | Backend Python | `/task/{id}?custom_task_ids=true` | Fetch original wait node task data | ✅ Bearer token |
| 875 | `await fetchSubtasksWithDetails(rootTask.id)` | Backend Python | Indirect - calls multiple task endpoints | Fetch all subtasks with details | ✅ Bearer token |

### Additional Supabase Edge Function Calls (Lines 568-585)

The `updateCustomField` function makes 3 additional calls within the approval submission:

| Call | Purpose | Endpoint | Authentication |
|------|---------|----------|----------------|
| Line 620 | Update HUMAN_APPROVED_ACTION field | `/api/v2/task/{id}/field/{fieldId}` | ❌ No auth headers |
| Line 621 | Update HUMAN_APPROVED_VALUE field | `/api/v2/task/{id}/field/{fieldId}` | ❌ No auth headers |
| Line 622 | Update WAIT_STATUS field | `/api/v2/task/{id}/field/{fieldId}` | ❌ No auth headers |

## Security Concerns

### 🚨 Critical Issues

1. **Undefined Edge Function URL (Line 568)**
   - `EDGE_FUNCTION_URL` variable is referenced but never defined
   - This will cause runtime errors when approval submissions are attempted

2. **Missing Authentication for Edge Function Calls (Lines 568-585)**
   - Supabase Edge Function calls lack authentication headers
   - No Bearer token or API key provided
   - Vulnerable to unauthorized access

3. **Mixed Authentication Patterns**
   - Backend calls properly use Bearer token authentication
   - Edge function calls have no authentication
   - Inconsistent security model

### ⚠️ Moderate Issues

1. **Hardcoded Configuration**
   - Backend URL hardcoded: `https://taskpages-backend.onrender.com` (Line 145)
   - Should use environment variables for different environments

2. **Error Handling Inconsistency**
   - Some API calls have comprehensive error handling
   - Edge function calls have minimal error handling

## API Call Flow Analysis

### Initialization Flow
1. **Authentication Check** → `checkAuthentication()` (Line 851)
2. **Find Process Root** → `findProcessLibraryRoot()` (Line 863)
   - Makes task API calls to traverse parent hierarchy
3. **Fetch Wait Task** → Direct task API call (Line 871)
4. **Fetch Subtasks** → `fetchSubtasksWithDetails()` (Line 875)
   - Makes multiple task API calls for subtask details

### Approval Submission Flow
1. **Update Fields** → 3 Edge Function calls (Lines 620-622)
   - ❌ **BROKEN**: Missing `EDGE_FUNCTION_URL` definition
   - ❌ **INSECURE**: No authentication
2. **Verify Update** → Backend API call (Line 631)
   - ✅ Properly authenticated

## Recommendations

### 🔥 Critical Fixes Required

1. **Define Edge Function URL**
   ```javascript
   const EDGE_FUNCTION_URL = 'https://your-supabase-project.supabase.co/functions/v1/clickup-proxy';
   ```

2. **Add Authentication to Edge Function Calls**
   ```javascript
   headers: {
       'Content-Type': 'application/json',
       'Authorization': `Bearer ${getAuthToken()}`,
       'apikey': 'your-supabase-anon-key'
   }
   ```

3. **Fix Broken Approval Flow**
   - The approval submission is completely broken due to undefined `EDGE_FUNCTION_URL`
   - Users cannot submit approvals in current state

### 🔧 Improvements

1. **Centralize Configuration**
   ```javascript
   const CONFIG = {
       BACKEND_URL: process.env.BACKEND_URL || 'https://taskpages-backend.onrender.com',
       EDGE_FUNCTION_URL: process.env.EDGE_FUNCTION_URL || 'https://your-project.supabase.co/functions/v1/clickup-proxy',
       SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY
   };
   ```

2. **Unified Authentication Helper**
   - Create single function for all API calls with consistent auth
   - Handle both backend and edge function authentication patterns

3. **Enhanced Error Handling**
   - Add retry logic for failed API calls
   - Better user feedback for network errors
   - Graceful degradation when services are unavailable

### 🎯 Security Hardening

1. **Input Validation**
   - Validate all API responses before processing
   - Sanitize user inputs before sending to APIs

2. **Rate Limiting**
   - Implement client-side rate limiting for API calls
   - Add exponential backoff for retries

3. **Environment-Based Configuration**
   - Remove hardcoded URLs and API keys
   - Use different endpoints for dev/staging/production

## Impact Assessment

- **High Impact**: Approval submissions are completely broken
- **Security Risk**: Edge function calls are unauthenticated
- **User Experience**: Users will encounter errors when trying to submit approvals
- **Data Integrity**: Task updates may fail silently or be rejected by APIs

This analysis reveals critical security and functionality issues that must be addressed immediately to restore proper application functionality.