# Backend Migration Plan: Wait Node API

## Executive Summary
This plan outlines the migration of ClickUp API calls from the frontend (wait-node.html) to a Python backend, eliminating direct API calls from the browser and improving security, performance, and maintainability.

---

## Current Architecture Analysis

### Security Issues with Current Implementation
1. **API credentials exposed** through Supabase edge function URL in frontend
2. **Team ID visible** in frontend code (Line 148)
3. **Custom field IDs exposed** in browser (Lines 151-166)
4. **No rate limiting** or request throttling
5. **No caching** of frequently accessed data

### Current API Call Pattern
```
Frontend → Supabase Edge Function → ClickUp API
```

---

## Proposed Python Backend Architecture

### New Architecture Pattern
```
Frontend → Python Backend API → ClickUp API
         ↓
    Local Cache/DB
```

### Technology Stack
- **Framework**: FastAPI (async support, automatic OpenAPI docs)
- **ClickUp Client**: Official Python SDK or httpx for async requests
- **Caching**: Redis for temporary data
- **Database**: PostgreSQL for persistent data (optional)
- **Authentication**: JWT tokens or session-based auth

---

## Python Backend Functions to Implement

### 1. Core ClickUp Service Class
```python
# clickup_service.py
class ClickUpService:
    def __init__(self):
        self.api_key = os.environ['CLICKUP_API_KEY']
        self.team_id = os.environ['CLICKUP_TEAM_ID']
        self.base_url = "https://api.clickup.com/api/v2"
    
    async def get_task(self, task_id: str, custom_task_ids: bool = False, include_subtasks: bool = False)
    async def update_custom_field(self, task_id: str, field_id: str, value: Any)
    async def find_process_library_root(self, start_task_id: str)
    async def fetch_subtasks_with_details(self, parent_task_id: str)
```

### 2. API Endpoints to Create

| Endpoint | Method | Frontend Function | Purpose |
|----------|--------|------------------|---------|
| `/api/wait-node/initialize` | GET | `initializeApp()` | Load all data for wait node interface |
| `/api/task/{task_id}` | GET | `makeApiRequest()` | Get task details |
| `/api/task/{task_id}/process-root` | GET | `findProcessLibraryRoot()` | Find process library root |
| `/api/task/{task_id}/subtasks-detailed` | GET | `fetchSubtasksWithDetails()` | Get all subtasks with details |
| `/api/task/{task_id}/approve` | POST | `handleSubmit()` | Submit approval and update fields |
| `/api/task/{task_id}/field/{field_id}` | PUT | `updateCustomField()` | Update single custom field |

---

## Migration Steps

### Phase 1: Backend Setup
1. **Create Python project structure**
   ```
   backend/
   ├── main.py           # FastAPI application
   ├── config.py         # Configuration management
   ├── services/
   │   ├── clickup.py    # ClickUp API service
   │   └── cache.py      # Redis caching service
   ├── routers/
   │   ├── wait_node.py  # Wait node endpoints
   │   └── tasks.py      # Task management endpoints
   ├── models/
   │   └── schemas.py    # Pydantic models
   └── requirements.txt
   ```

2. **Environment variables**
   ```env
   CLICKUP_API_KEY=your_key_here
   CLICKUP_TEAM_ID=9011954126
   REDIS_URL=redis://localhost:6379
   CORS_ORIGINS=["http://localhost:3000"]
   ```

### Phase 2: Implement Core Services

#### 2.1 ClickUp Service Implementation
```python
# services/clickup.py
import httpx
from typing import Optional, Dict, Any, List

class ClickUpService:
    def __init__(self, api_key: str, team_id: str):
        self.api_key = api_key
        self.team_id = team_id
        self.headers = {"Authorization": api_key}
        self.base_url = "https://api.clickup.com/api/v2"
    
    async def get_task(
        self, 
        task_id: str, 
        custom_task_ids: bool = False,
        include_subtasks: bool = False
    ) -> Dict[str, Any]:
        params = {"team_id": self.team_id}
        if custom_task_ids:
            params["custom_task_ids"] = "true"
        if include_subtasks:
            params["include_subtasks"] = "true"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/task/{task_id}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
    
    async def update_custom_field(
        self,
        task_id: str,
        field_id: str,
        value: Any
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/task/{task_id}/field/{field_id}",
                headers=self.headers,
                json={"value": value}
            )
            response.raise_for_status()
            return response.json()
```

#### 2.2 Wait Node Router
```python
# routers/wait_node.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from services.clickup import ClickUpService

router = APIRouter(prefix="/api/wait-node")

@router.get("/initialize/{task_id}")
async def initialize_wait_node(
    task_id: str,
    clickup: ClickUpService = Depends(get_clickup_service)
):
    """Combined endpoint to fetch all necessary data for wait node"""
    try:
        # Find process library root
        root_task = await clickup.find_process_library_root(task_id)
        
        # Get wait task details
        wait_task = await clickup.get_task(task_id, custom_task_ids=True)
        
        # Get all subtasks
        subtasks = await clickup.fetch_subtasks_with_details(root_task["id"])
        
        return {
            "root_task": root_task,
            "wait_task": wait_task,
            "subtasks": subtasks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve/{task_id}")
async def approve_task(
    task_id: str,
    approval_data: Dict[str, Any],
    clickup: ClickUpService = Depends(get_clickup_service)
):
    """Handle approval submission"""
    try:
        # Update multiple fields in parallel
        updates = []
        for field_id, value in approval_data.items():
            updates.append(
                clickup.update_custom_field(task_id, field_id, value)
            )
        
        results = await asyncio.gather(*updates)
        
        # Verify the update
        verified_task = await clickup.get_task(task_id, custom_task_ids=True)
        
        return {
            "success": True,
            "task": verified_task,
            "updates": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Phase 3: Frontend Modifications

#### 3.1 New API Service for Frontend
```javascript
// api-service.js
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

class WaitNodeAPI {
    async initializeWaitNode(taskId) {
        const response = await fetch(`${BACKEND_URL}/api/wait-node/initialize/${taskId}`);
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        return response.json();
    }
    
    async submitApproval(taskId, approvalData) {
        const response = await fetch(`${BACKEND_URL}/api/wait-node/approve/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(approvalData)
        });
        if (!response.ok) throw new Error(`API error: ${response.status}`);
        return response.json();
    }
}
```

#### 3.2 Replace Direct API Calls
```javascript
// Old code (remove):
const response = await fetch(EDGE_FUNCTION_URL, {...});

// New code:
const api = new WaitNodeAPI();
const data = await api.initializeWaitNode(taskId);
```

### Phase 4: Testing & Deployment

1. **Unit Tests** for ClickUp service methods
2. **Integration Tests** for API endpoints
3. **Load Testing** for performance validation
4. **Security Testing** for authentication/authorization
5. **Deployment** using Docker/Kubernetes

---

## Benefits of Migration

### Security Improvements
- ✅ API keys stored securely on backend
- ✅ Rate limiting and throttling implementation
- ✅ Request validation and sanitization
- ✅ Audit logging of all API calls

### Performance Improvements
- ✅ Server-side caching reduces API calls
- ✅ Batch operations for multiple updates
- ✅ Connection pooling for better throughput
- ✅ Background task processing capability

### Maintainability Improvements
- ✅ Centralized error handling
- ✅ Easier debugging with server logs
- ✅ Version control for API changes
- ✅ Simplified frontend code

### Scalability Improvements
- ✅ Horizontal scaling capability
- ✅ Queue-based processing for heavy operations
- ✅ Database persistence for offline capability
- ✅ WebSocket support for real-time updates

---

## Implementation Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Backend Setup | 1 day | Project structure, dependencies, configuration |
| Core Services | 2 days | ClickUp service, caching, error handling |
| API Endpoints | 2 days | All routes, validation, documentation |
| Frontend Updates | 1 day | Replace API calls, testing |
| Testing | 2 days | Unit, integration, load tests |
| Deployment | 1 day | Docker, CI/CD, monitoring |

**Total: ~9 days**

---

## Risk Mitigation

1. **Rollback Plan**: Keep Supabase edge function active during transition
2. **Feature Flags**: Gradual rollout with ability to switch between old/new
3. **Monitoring**: Comprehensive logging and alerting from day 1
4. **Documentation**: OpenAPI/Swagger docs auto-generated
5. **Error Recovery**: Implement circuit breakers and retries

---

## Next Steps

1. Review and approve this plan
2. Set up Python development environment
3. Create backend repository
4. Begin Phase 1 implementation
5. Schedule testing with stakeholders