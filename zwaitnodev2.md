# API Call Analysis for wait-node-v2.html

## Overview
This document provides a comprehensive map of every API call made in the wait-node-v2.html file, from top to bottom. The application primarily interacts with a Python Flask backend at either `http://localhost:5678` (development) or `https://taskpages-backend.onrender.com` (production).

## API Calls Mapping

| Line # | Function/Component | API Endpoint | Method | Service | Purpose | Auth |
|--------|-------------------|--------------|--------|---------|---------|------|
| 222 | WaitNodeAPI.request() | `${this.baseUrl}${endpoint}` | Variable | Backend (Flask) | Generic authenticated request wrapper for all API calls | Bearer token |
| 254 | WaitNodeAPI.getTask() | `/api/task/${taskId}` | GET | Backend (Flask) | Retrieve task details with optional query parameters | Bearer token |
| 259 | WaitNodeAPI.initializeWaitNode() | `/api/wait-node/initialize/${taskId}` | GET | Backend (Flask) | Initialize wait node with all required data (root task, subtasks, etc.) | Bearer token |
| 264 | WaitNodeAPI.submitApproval() | `/api/wait-node/approve/${taskId}` | POST | Backend (Flask) | Submit human approval decision for wait node | Bearer token |
| 540 | initializeApp() | `/api/wait-node/initialize/${taskId}` | GET | Backend (Flask) | Main initialization call to load all app data | Bearer token |
| 588 | ApprovalModule.handleSubmit() | `/api/wait-node/approve/${taskId}` | POST | Backend (Flask) | Submit approval data through backend API | Bearer token |
| 817 | CommentsSection.loadInitialComments() | `/api/task/${mainTask.id}/comments?limit=5` | GET | Backend (Flask) | Load initial set of task comments | Bearer token |
| 853 | CommentsSection.loadMoreComments() | `/api/task/${mainTask.id}/comments?start=${comments.length}&limit=5` | GET | Backend (Flask) | Load additional comments with pagination | Bearer token |
| 1018 | StepDetailsPanel.loadStepComments() | `/api/task/${stepId}/comments?limit=5` | GET | Backend (Flask) | Load comments for a specific step/subtask | Bearer token |
| 1053 | StepDetailsPanel.loadMoreStepComments() | `/api/task/${selectedStep.id}/comments?start=${stepComments.length}&limit=5` | GET | Backend (Flask) | Load additional step comments with pagination | Bearer token |

## API Service Categories

### Backend Flask API Endpoints
All API calls go through the WaitNodeAPI class which handles authentication and provides a consistent interface to the Python Flask backend.

**Base URL Configuration (Lines 146-148):**
- Development: `http://localhost:5678`
- Production: `https://taskpages-backend.onrender.com`

### Authentication Pattern
Every API call includes:
- **Authorization Header**: `Bearer ${authToken}` (Line 225)
- **Content-Type**: `application/json` (Line 226)
- **Token Source**: `localStorage.getItem('auth_token')` (Line 199)
- **Auth Failure Handling**: Redirects to `/index.html` on 401 responses

## Key API Endpoints

### 1. Wait Node Operations
- **Initialize**: `/api/wait-node/initialize/${taskId}` - Comprehensive data loading
- **Approve**: `/api/wait-node/approve/${taskId}` - Submit human approval decisions

### 2. Task Operations
- **Get Task**: `/api/task/${taskId}` - Basic task retrieval
- **Get Comments**: `/api/task/${taskId}/comments` - Comment retrieval with pagination

### 3. Authentication Flow
- **Token Storage**: Uses localStorage for auth token persistence
- **Redirect Behavior**: Automatic redirect to `/index.html` on authentication failure
- **Token Validation**: Every request validates token before execution

## Error Handling Patterns

1. **Authentication Errors** (401): Remove token and redirect to login
2. **API Errors**: JSON error response parsing and user-friendly messaging
3. **Network Errors**: Console logging and error state management

## Data Flow Summary

1. **App Initialization**: Single call to `/api/wait-node/initialize/${taskId}` loads all required data
2. **Comment Loading**: Separate paginated calls for main task and step-specific comments
3. **Approval Submission**: Single POST to `/api/wait-node/approve/${taskId}` with form data
4. **Authentication**: Persistent token-based auth with automatic redirect on failure

## Notes

- No direct ClickUp API calls are made from the frontend
- All ClickUp interactions are proxied through the Flask backend
- The backend handles authentication, data aggregation, and business logic
- Frontend focuses on UI/UX and user interaction handling