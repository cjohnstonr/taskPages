# CHANGELOG

## [2025-09-30] - Type: UI
- Change: Complete redesign of task-helper interface to prioritize escalation context over custom fields
- Files: backend/templates/secured/task-helper.html
- State impact: None
- Field mutations: None
- Performance: Improved initial render with collapsed sections

**Major Changes**:
- Added CollapsibleSection component for clean, organized interface
- Implemented CommentsSection with avatar display and pagination (borrowed from wait-node-v2.html)
- Created TaskHeader component showing task context with parent breadcrumb
- Custom fields now hidden by default in collapsible section
- Restructured layout: Header → Escalation → Comments → Description → Custom Fields
- Added smooth accordion animations for professional feel
- Comments load on-demand when section expanded

**UI Improvements**:
- Custom fields no longer dominate the interface
- Focus shifted to escalation workflow
- Added user avatars with initials in comments
- Show more/less for long comments
- Load more pagination for comment threads
- Consistent collapsible pattern throughout

## [2025-09-28] - Type: Pipeline
- Change: Fixed AI summary NoneType error by handling explicit None values in context data
- Files: backend/app_secure.py (lines 1002, 1014-1016), backend/templates/secured/task-helper.html (lines 332-333)
- State impact: None
- Field mutations: None
- Performance: No measurable impact on endpoint performance

**Root Cause**: When frontend sent `context: {task: null}`, the code `context.get('task', {})` returned `None` instead of `{}` because the key existed with value None. This caused `task_info.get('status')` to fail with NoneType error.

**Solution**: 
- Backend: Changed to `context.get('task') or {}` pattern (lines 1014-1016)
- Frontend: Added defensive `task || {}` to never send null values (lines 332-333)

**Impact**: AI escalation summary now handles all edge cases including null/undefined task data.

## [2025-09-27] - Type: Pipeline
- Change: Fixed AI summary functionality regression by correcting session access pattern in user role endpoint
- Files: backend/app_secure.py
- State impact: None
- Field mutations: None
- Performance: No measurable impact on endpoint performance

**Root Cause**: The `/api/user/role` endpoint (added in commit a07a1c6) was using vulnerable session chaining `session.get('user', {}).get('email', '')` which caused NoneType errors when session state was affected by state management changes.

**Solution**: Updated user role endpoint to use safe `request.user.get('email', '')` pattern (consistent with other endpoints that were already fixed).

**Impact**: AI escalation summary functionality now works correctly. Frontend initialization no longer fails due to user role endpoint errors.