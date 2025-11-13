# CHANGELOG

## [2025-11-12] - Type: State|UI|Field
- Change: Refactored escalation resolved state logic and added reopen functionality
- Files: backend/templates/secured/escalationv3.html, backend/app_secure.py
- State impact: Changed isResolved condition from compound logic to explicit status check only
- Field mutations: Escalation_Status field (8d784bd0) - added write capability via reopen endpoint
- Performance: No measurable impact - single API call for reopen action

**State Management Changes**:
- Removed supervisorResponse from isResolved condition (line 1467)
- Before: `const isResolved = escalationStatus === 'RESOLVED' || supervisorResponse;`
- After: `const isResolved = escalationStatus === 'RESOLVED';`
- Rationale: Explicit status control prevents implicit state changes from text field updates

**New Functionality**:
- Added "Reopen Escalation" button in resolved state UI with confirmation dialog
- Created `/api/task-helper/reopen-escalation/<task_id>` POST endpoint
- Reopen action sets Escalation_Status to 0 (Not Escalated) for resubmission
- Maintains historical data (supervisor response, timestamps) for audit trail
- Adds ClickUp comment with reopen metadata (user, timestamp)

**Security & Audit**:
- Endpoint protected with @login_required and rate limiting (10 per minute)
- Full audit logging with user email and timestamps
- ClickUp comment records reopening action for compliance

## [2025-11-12] - Type: UI
- Change: Implemented Markdown rendering for AI Summary and AI Suggestion dialog boxes with mobile-responsive styling
- Files: backend/templates/secured/escalationv3.html
- State impact: None
- Field mutations: None
- Performance: No measurable impact - leverages existing marked.js and DOMPurify libraries

**Major Changes**:
- Updated all AI Summary boxes (3 locations) to render Markdown using `renderMarkdown()` helper
- Updated all AI Suggestion boxes (3 locations) to render Markdown using `renderMarkdown()` helper
- Added comprehensive mobile-responsive CSS for `.prose` and `.prose-sm` classes
- Implemented word-break for code elements to prevent horizontal overflow on mobile
- Added mobile-specific media query (@max-width: 640px) for optimized font sizes and spacing

**UI Improvements**:
- AI-generated content now supports formatted text: headers, bold, italics, lists, code blocks
- Improved readability on mobile devices with responsive typography
- Code blocks properly styled with syntax highlighting and horizontal scrolling
- Blockquotes and lists properly indented and styled
- Safe HTML rendering with DOMPurify sanitization

**Technical Details**:
- Uses existing `renderMarkdown(text)` function: `DOMPurify.sanitize(marked.parse(text))`
- Applied `prose prose-sm max-w-none` classes for consistent styling
- Mobile optimizations include reduced font sizes, adjusted padding, and full-width code blocks
- All markdown rendering uses `dangerouslySetInnerHTML` with DOMPurify protection

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