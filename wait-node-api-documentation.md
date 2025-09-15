# Wait Node API Documentation

## Overview
This document catalogs all API calls made to external endpoints in the `wait-node.html` file, specifically focusing on Supabase Edge Function calls that proxy to ClickUp API.

## Primary External Endpoint

### Supabase Edge Function - Dynamic Request Dispatcher
- **URL**: `https://efmbjvncbvoovafxwhjw.supabase.co/functions/v1/dynamic-request-dispatcher`
- **Line**: 145
- **Constant**: `EDGE_FUNCTION_URL`

---

## API Call Functions

### 1. `makeApiRequest(endpoint)`
**Location**: Lines 189-219  
**Description**: Core function that routes all GET requests through the Supabase edge function to access ClickUp API v2 endpoints.
**ClickUp API**: Various endpoints (see specific usage below)

**Implementation Details**:
- Automatically appends `team_id` parameter if not present
- Sends POST request to edge function with:
  - `method`: 'GET'
  - `endpoint`: Prefixed with '/api/v2'
  - `profile`: 'homeowner'
- Returns parsed JSON response

---

### 2. `findProcessLibraryRoot(startTaskId)`
**Location**: Lines 222-250  
**Description**: Traverses up the task hierarchy to find the top-level Process Library parent task.

**API Calls Made**:
| Line | Function Call | ClickUp API Endpoint |
|------|--------------|---------------------|
| 223 | `makeApiRequest('/task/${startTaskId}?custom_task_ids=true')` | GET `/api/v2/task/{task_id}` |
| 235 | `makeApiRequest('/task/${currentTask.parent}?custom_task_ids=true')` | GET `/api/v2/task/{task_id}` |

---

### 3. `fetchSubtasksWithDetails(parentTaskId)`
**Location**: Lines 253-288  
**Description**: Retrieves all subtasks of a parent task with their complete custom field data.

**API Calls Made**:
| Line | Function Call | ClickUp API Endpoint |
|------|--------------|---------------------|
| 255 | `makeApiRequest('/task/${parentTaskId}?include_subtasks=true')` | GET `/api/v2/task/{task_id}` |
| 267 | `makeApiRequest('/task/${subtask.id}?custom_task_ids=true')` | GET `/api/v2/task/{task_id}` |

---

### 4. `updateCustomField(taskId, fieldId, value)`
**Location**: Lines 544-563  
**Description**: Updates a specific custom field value for a task through the edge function.
**ClickUp API**: POST `/api/v2/task/{task_id}/field/{field_id}`

**Implementation Details**:
- **Line 545-556**: Sends POST request to edge function with:
  - `method`: 'POST'
  - `endpoint`: `/api/v2/task/${taskId}/field/${fieldId}`
  - `profile`: 'homeowner'
  - `params`: { value }
- Returns parsed JSON response

---

### 5. `initializeApp()`
**Location**: Lines 822-857  
**Description**: Main initialization function that orchestrates data fetching when the app loads.

**API Calls Made**:
| Line | Function Call | ClickUp API Endpoint |
|------|--------------|---------------------|
| 834 | `findProcessLibraryRoot(taskId)` | GET `/api/v2/task/{task_id}` (multiple calls) |
| 842 | `makeApiRequest('/task/${taskId}?custom_task_ids=true')` | GET `/api/v2/task/{task_id}` |
| 846 | `fetchSubtasksWithDetails(rootTask.id)` | GET `/api/v2/task/{task_id}` (multiple calls) |

---

### 6. `handleSubmit()` (within ApprovalModule)
**Location**: Lines 566-628  
**Description**: Handles approval form submission and updates multiple custom fields.

**API Calls Made**:
| Line | Function Call | ClickUp API Endpoint |
|------|--------------|---------------------|
| 597 | `updateCustomField(taskData.id, FIELD_IDS.HUMAN_APPROVED_ACTION, aiProposedAction)` | POST `/api/v2/task/{task_id}/field/{field_id}` |
| 598 | `updateCustomField(taskData.id, FIELD_IDS.HUMAN_APPROVED_VALUE, valueToSubmit)` | POST `/api/v2/task/{task_id}/field/{field_id}` |
| 599 | `updateCustomField(taskData.id, FIELD_IDS.WAIT_STATUS, 3)` | POST `/api/v2/task/{task_id}/field/{field_id}` |
| 608 | `makeApiRequest('/task/${taskData.id}?custom_task_ids=true')` | GET `/api/v2/task/{task_id}` |

---

## Summary of ClickUp API Endpoints Used

All endpoints are accessed through the Supabase edge function proxy:

| ClickUp API Endpoint | HTTP Method | Purpose | Query Parameters |
|---------------------|-------------|---------|-----------------|
| `/api/v2/task/{task_id}` | GET | Fetch task details, parent tasks, subtasks | `custom_task_ids=true`, `include_subtasks=true`, `team_id={team_id}` |
| `/api/v2/task/{task_id}/field/{field_id}` | POST | Update custom field values | Body: `{ value: <field_value> }` |

**Note**: The Supabase edge function endpoint paths match the ClickUp API paths exactly, just proxying the requests with authentication.

---

## Request Authentication
- All requests include `profile: 'homeowner'` parameter
- Authentication is handled by the Supabase edge function
- Team ID (`9011954126`) is automatically appended to all requests

---

## Error Handling
- All API functions include try-catch blocks
- Errors are logged to console with detailed messages
- Failed requests throw errors with status codes and response data
- Verification step after updates to ensure data persistence (Line 608)