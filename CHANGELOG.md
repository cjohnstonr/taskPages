# CHANGELOG

## [2025-09-27] - Type: Pipeline
- Change: Fixed AI summary functionality regression by correcting session access pattern in user role endpoint
- Files: backend/app_secure.py
- State impact: None
- Field mutations: None
- Performance: No measurable impact on endpoint performance

**Root Cause**: The `/api/user/role` endpoint (added in commit a07a1c6) was using vulnerable session chaining `session.get('user', {}).get('email', '')` which caused NoneType errors when session state was affected by state management changes.

**Solution**: Updated user role endpoint to use safe `request.user.get('email', '')` pattern (consistent with other endpoints that were already fixed).

**Impact**: AI escalation summary functionality now works correctly. Frontend initialization no longer fails due to user role endpoint errors.