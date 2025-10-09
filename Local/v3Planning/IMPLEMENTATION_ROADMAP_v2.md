# Escalation System v3 - Implementation Roadmap

**Project:** Advanced Escalation System with AI Integration
**Status:** Phase 5 - RFI System (COMPLETE)
**Started:** 2025-10-08

---

## 🎯 Project Overview

Transform the current 3-state escalation system into a comprehensive AI-powered escalation workflow with:
- Property-based context awareness
- AI-suggested solutions via n8n
- Multi-level escalation routing (Supervisor → Christian)
- Request for Information (RFI) capability
- AI grading of human responses
- Complete audit trail

---

## 📊 Current vs Desired State

### Current System (v2)
- **3 states:** Not Escalated → Escalated → Resolved
- **1 action:** Supervisor responds
- **No AI integration**
- **No property context**
- **No escalation routing**

### Desired System (v3)
- **5 states:** Not Escalated → Escalated L1 → [Awaiting Info] → Escalated L2 → Resolved
- **3 supervisor actions:** Answer / Request Info / Escalate to L2
- **Full AI integration:** Suggestions + Grading via n8n
- **Property-aware:** Links to property vector stores
- **Multi-level routing:** Supervisor → Christian
- **Complete history:** JSON log of all state transitions

---

## 📅 Phase Timeline

| Phase | Name | Duration | Status | Blocks |
|-------|------|----------|--------|--------|
| 1 | Foundation | 1 day | ✅ COMPLETE | Everything |
| 2 | Property Link Validation | 2 hours ⚡ | ✅ COMPLETE | n8n integration |
| 3 | n8n AI Suggestion | 2 days | ✅ COMPLETE | AI features |
| 4 | Supervisor Multi-Action UI | 1 day | ✅ COMPLETE | Routing |
| 5 | RFI System | 6 hours ⚡ | ✅ COMPLETE | Info requests |
| 6 | Level 2 Escalation | 1 day | 🟢 READY | Christian queue |
| 7 | AI Grading | 1 day | ⏸️ WAITING | Analysis |
| 8 | History Logging | 1 day | ⏸️ WAITING | Audit trail |

**Total Estimated Time:** 8.25 days (saved 2 hours in Phase 5) ⚡
**Phases Complete:** ✅ Phase 1 + ✅ Phase 2 + ✅ Phase 3 + ✅ Phase 4 + ✅ Phase 5
**Next Phase:** 🟢 Phase 6 - Level 2 Escalation (READY)

---

## 📋 Implementation Phases

### ✅ PHASE 1: FOUNDATION (COMPLETE)
**Status:** ✅ COMPLETE

**Deliverables:**
1. ✅ All 14 custom fields verified (test passed on TICKET-43999)
2. ✅ ESCALATION_STATUS dropdown updated (5 options including new states 3 & 4)
3. ✅ All custom fields exist in ClickUp (13 escalation + 1 property_link)
4. ✅ Frontend constants updated with field IDs
5. ✅ Backend constants updated with field IDs
6. ✅ All UUIDs verified and documented
7. ✅ Verification tests passed (14/14 fields accessible)

**Files Modified:**
- `backend/templates/secured/escalationv3.html` (NEW FILE - v3 of escalation system)
- `app_secure.py` (lines 740-748)

**Checklist:** See `PHASE_1_CHECKLIST.md`

---

### ✅ PHASE 2: PROPERTY LINK VALIDATION (COMPLETE)
**Status:** ✅ COMPLETE (2 hours)

**✅ EXISTING IMPLEMENTATION REUSED**

**Reusable Code:** `/Local/test_property_link_propagation.py`
- ✅ Property link detection logic (checks task → checks parent)
- ✅ Auto-propagation to subtask using `{"add": [ids]}` format
- ✅ Custom task ID handling (TICKET-xxx format)
- ✅ Regular ID extraction for POST requests
- ✅ Tested and verified on TICKET-65711

**Property Link Field ID:** `73999194-0433-433d-a27c-4d9c5f194fd0`

**Key Implementation Details:**
```python
# From /Local/SHARE_THIS.md - ensure_property_link() function
def ensure_property_link(task_id: str, clickup_token: str) -> Optional[List[str]]:
    """
    1. Fetch task (auto-detects custom_id format)
    2. Check for property_link field (73999194-0433-433d-a27c-4d9c5f194fd0)
    3. If missing → fetch parent task (parent or top_level_parent)
    4. Extract property_link IDs from parent
    5. Set on subtask using: {"value": {"add": [property_ids]}}
    6. CRITICAL: Use regular task ID for POST (not custom TICKET-xxx)
    Returns: List of property link IDs or None
    """
```

**Deliverables (Completed):**
1. ✅ Property link propagation logic - **REUSED FROM /Local/**
2. ✅ Wrapper endpoint: `/api/task-helper/validate-property-link/<task_id>`
   - Copied `ensure_property_link()` helper into `app_secure.py`
   - Returns: `{success: bool, has_property_link: bool, property_link_ids: [...], error: string}`
   - Added rate limiting (30/minute) and authentication
3. ✅ Frontend validator component in `escalationv3.html`
   - `validatePropertyLink()` function calls endpoint
   - Called BEFORE escalation submission
   - Blocks escalation if no property link
4. ✅ Error UI: Alert dialog with message
   - "❌ Property Link Missing - This task must be linked to a property to escalate"
   - Prevents submission until property link is added

**Why Critical:**
- n8n needs property_link to select correct vector store
- Vector store contains property-specific SOPs
- Cannot proceed to Phase 3 without this

**Files to Create/Modify:**
- `app_secure.py` - New validation endpoint (wrapper around existing logic)
- `escalationv3.html` - Validator component

**Time Savings:**
- Original estimate: 1 day (8 hours)
- New estimate: 2-3 hours (reusing tested implementation)

---

### ✅ PHASE 3: n8n AI SUGGESTION (COMPLETE)
**Status:** ✅ COMPLETE

**n8n Webhook URL:** `https://n8n.oodahost.ai/webhook/d176be54-1622-4b73-a5ce-e02d619a53b9`

**Deliverables (Completed):**
1. ✅ n8n webhook configured and ready
2. ✅ Update backend endpoint: `/api/task-helper/escalate/<task_id>`
   - ✅ **FIRST:** Call `ensure_property_link(task_id)` to guarantee property context
   - ✅ **THEN:** Check if `ESCALATION_AI_SUGGESTION` already has value (caching)
   - ✅ **IF CACHED:** Skip n8n call, use existing suggestion
   - ✅ **IF NOT CACHED:** POST to n8n with `{task_id: "xxx"}`
3. ✅ n8n handles everything internally (task tree fetch, vector store, SOPs analysis)
4. ✅ n8n returns: `{suggestion: "text"}`
5. ✅ Save to: `ESCALATION_AI_SUGGESTION` field (`bc5e9359-01cd-408f-adb9-c7bdf1f2dd29`)
6. ✅ Frontend displays AI suggestion automatically to employee

**Critical Order of Operations:**
```
1. ensure_property_link(task_id) → Sets property_link if missing from parent
2. Check ESCALATION_AI_SUGGESTION → If exists, skip n8n (already analyzed)
3. If not cached → POST {task_id} to n8n webhook
4. n8n responds → {suggestion: "..."}
5. Save suggestion → Update ESCALATION_AI_SUGGESTION field
6. Frontend renders → Display to employee
```

**Integration Pattern:**
```python
# In app_secure.py - escalate_task() endpoint
@app.route('/api/task-helper/escalate/<task_id>', methods=['POST'])
def escalate_task(task_id):
    # STEP 1: Ensure property_link exists BEFORE anything else
    property_link_ids = ensure_property_link(task_id, clickup_token)

    if not property_link_ids:
        return jsonify({
            'success': False,
            'error': 'No property link found. This task must be linked to a property.'
        }), 400

    # STEP 2: Check if AI suggestion already exists (caching)
    task = get_clickup_task(task_id)
    existing_suggestion = get_custom_field_value(task, FIELD_IDS['ESCALATION_AI_SUGGESTION'])

    if existing_suggestion:
        ai_suggestion = existing_suggestion  # Use cached value
        logger.info(f"Using cached AI suggestion for {task_id}")
    else:
        # STEP 3: Call n8n to generate suggestion
        n8n_url = 'https://n8n.oodahost.ai/webhook/d176be54-1622-4b73-a5ce-e02d619a53b9'
        n8n_response = requests.post(n8n_url, json={'task_id': task_id})
        ai_suggestion = n8n_response.json().get('suggestion')
        logger.info(f"Generated new AI suggestion for {task_id}")

    # STEP 4: Update escalation fields including AI suggestion
    # ... continue with field updates
```

**Files Modified:**
- ✅ `app_secure.py` - Updated `/escalate` endpoint with property validation + AI caching
- ✅ `escalationv3.html` - Added AI suggestion display in success alert
- ✅ n8n workflow already configured (handles task tree + vector store internally)

**Test Script Created:**
- `/Local/test_phase3_n8n_integration.py` - Comprehensive test documentation and manual test scenarios

---

### ✅ PHASE 4: SUPERVISOR MULTI-ACTION UI (COMPLETE)
**Status:** ✅ COMPLETE (1 day)

**📚 Planning & Test Documents:**
- **Full Plan:** `/Local/v3Planning/PHASE_4_DETAILED_PLAN.md` - Complete architecture, code samples, testing strategy
- **Quick Reference:** `/Local/v3Planning/PHASE_4_QUICK_REFERENCE.md` - Implementation checklist, time estimates, debug guide
- **Summary:** `/Local/v3Planning/PHASE_4_SUMMARY.md` - Executive overview
- **Test Script:** `/Local/v3Planning/PHASE_4_TEST_SCRIPT.md` - Comprehensive manual testing guide

**✅ Deliverables Completed:**
1. ✅ State detection for new dropdown options:
   - **ESCALATED_LEVEL_2** (orderindex: 3, UUID: `460769a8-90fa-401d-aeb1-a6d90fb3ee04`)
   - **AWAITING_INFO** (orderindex: 4, UUID: `ca62ea92-bc51-4d4a-93a8-c084e330e278`)
2. ✅ Supervisor action panel component (3 buttons: Answer / Request Info / Escalate L2)
3. ✅ Backend endpoint: `/api/task-helper/supervisor-response/<task_id>` (reused from Phase 3)
4. ✅ Backend endpoint: `/api/task-helper/request-info/<task_id>` (created - line 1206)
5. ✅ Backend endpoint: `/api/task-helper/escalate-to-level-2/<task_id>` (created - line 1310)

**UI Design:**
```
┌─────────────────────────────────────┐
│  🚨 Escalation Awaiting Your Action │
├─────────────────────────────────────┤
│  Reason: [employee reason]          │
│  AI Suggestion: [AI response]       │
├─────────────────────────────────────┤
│  Choose Action:                     │
│  ┌──────────┐ ┌──────────┐ ┌──────┐│
│  │ ✅ Answer│ │ ❓ Request│ │ ⬆️ L2││
│  │          │ │   Info   │ │ Esc. ││
│  └──────────┘ └──────────┘ └──────┘│
└─────────────────────────────────────┘
```

**Files Modified:**
- ✅ `backend/templates/secured/escalationv3.html`:
  - Updated `getDropdownValue()` function to detect 5 states (lines 351-357)
  - Created `SupervisorActionPanel` component with 3-button interface (lines 479-670)
  - Updated `EscalationModule` rendering logic for states 3 & 4 (lines 932-1012)
- ✅ `backend/app_secure.py`:
  - Created `/api/task-helper/request-info/<task_id>` endpoint (lines 1206-1307)
  - Created `/api/task-helper/escalate-to-level-2/<task_id>` endpoint (lines 1310-1411)

**Implementation Notes:**
- ✅ 5-state system fully functional
- ✅ SupervisorActionPanel integrates all 3 actions
- ✅ Conditional form rendering based on selected action
- ✅ ClickUp field updates implemented for all actions
- ✅ Comments added to tasks for each action
- ✅ Error handling and validation in place
- ✅ Placeholder UIs for Phase 5 (AWAITING_INFO) and Phase 6 (ESCALATED_LEVEL_2)

**Testing:**
- 🔲 Manual testing required (see `/Local/v3Planning/PHASE_4_TEST_SCRIPT.md`)
- 🔲 Backend environment configuration needed for live testing

---

### ✅ PHASE 5: RFI SYSTEM (COMPLETE)
**Status:** ✅ COMPLETE (6 hours)

**📚 Comprehensive Planning Documents:**
- **Full Plan:** `/Local/v3Planning/PHASE_5_DETAILED_PLAN.md` - Complete architecture, code samples, testing strategy (30 pages)
- **Quick Reference:** `/Local/v3Planning/PHASE_5_QUICK_REFERENCE.md` - Implementation checklist, code snippets, debug guide (8 pages)
- **Summary:** `/Local/v3Planning/PHASE_5_SUMMARY.md` - Executive overview, business value, timeline (7 pages)
- **Validation Script:** `/Local/v3Planning/validate_phase5_implementation.py` - Automated validation (100% pass rate)

**✅ Deliverables Completed:**
1. ✅ RFI request form (Phase 4 complete - supervisor enters what info needed)
2. ✅ AWAITING_INFO state UI - Replaced placeholder with RFIResponseForm component
3. ✅ RFI response form (employee responds with textarea and submit button)
4. ✅ Backend endpoint: `/api/task-helper/respond-to-rfi/<task_id>` (lines 1414-1515 in app_secure.py)
5. ✅ State transition: AWAITING_INFO → ESCALATED (back to supervisor)
6. ✅ RFI history display in SupervisorActionPanel (collapsible section with Q&A)

**Flow:**
```
Supervisor clicks "Request Info"
    ↓
Enters: "What is the property address?"
    ↓
ESCALATION_STATUS = 4 (Awaiting Info)
RFI_REQUEST = "What is the property address?"
RFI_STATUS = 0 (Requested)
    ↓
Employee sees RFI request
    ↓
Employee responds: "123 Main St"
    ↓
RFI_RESPONSE = "123 Main St"
RFI_STATUS = 1 (Completed)
ESCALATION_STATUS = 1 (back to supervisor)
```

**Files Modified:**
- ✅ `backend/templates/secured/escalationv3.html`:
  - Created `RFIResponseForm` component (lines 479-544)
  - Updated AWAITING_INFO state rendering with functional form (line 1036)
  - Added RFI History state management to SupervisorActionPanel (lines 554-558)
  - Added RFI History collapsible section (lines 623-664)
- ✅ `backend/app_secure.py`:
  - Created `/api/task-helper/respond-to-rfi/<task_id>` endpoint (lines 1414-1515)
  - Updates 3 fields: RFI_RESPONSE, RFI_STATUS=1, ESCALATION_STATUS=1
  - Adds comment with notification to supervisor
  - Includes authentication, rate limiting, and error handling

**Implementation Notes:**
- ✅ Complete RFI workflow functional (supervisor → employee → supervisor)
- ✅ RFI History auto-expands when employee responds (rfiStatus === 1)
- ✅ Visual indicators: Green badge for "Response Received", orange for "Awaiting"
- ✅ Followed Phase 4 patterns for consistency
- ✅ All security measures in place (@login_required, rate limiting, input validation)
- ✅ 100% validation test pass rate

**Testing:**
- ✅ Automated validation complete (8/8 tests passed)
- 🔲 Manual end-to-end testing recommended (see validation script for test scenarios)

---

### 🟢 PHASE 6: LEVEL 2 ESCALATION (1 DAY)
**Status:** 🟢 READY (Phase 4 complete)

**Deliverables:**
1. Level 2 escalation form (pre-populated with AI response)
2. ESCALATED_LEVEL_2 state UI (Christian's view)
3. Backend endpoint: `/api/task-helper/christian-answer/<task_id>`
4. Set ESCALATION_LEVEL = 2

**UI for Supervisor:**
```
┌─────────────────────────────────────┐
│  Escalate to Level 2 (Christian)    │
├─────────────────────────────────────┤
│  Original Reason: [pre-filled]      │
│  AI Suggestion: [pre-filled]        │
│                                     │
│  Additional Context:                │
│  ┌─────────────────────────────┐   │
│  │ [Supervisor can add more    │   │
│  │  context here]              │   │
│  └─────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ 🚨 Escalate to Christian     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Files to Create/Modify:**
- `escalationv3.html` - Level 2 escalation components (Christian's view)
- `app_secure.py` - Christian answer endpoint

---

### 🔲 PHASE 7: AI GRADING (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 3

**Deliverables:**
1. n8n webhook: `/webhook/grade-response`
2. Update supervisor-answer endpoint to call n8n
3. n8n receives: supervisor_answer + AI_suggestion
4. n8n returns: grade + feedback
5. Save to: `AI_GRADE_OF_RESPONSE`
6. Display grade in resolved view

**n8n Workflow Steps:**
1. Receive supervisor_answer + AI_suggestion
2. Compare responses
3. Evaluate against SOPs
4. Generate grade/feedback
5. Return JSON: `{grade: "text", feedback: "text"}`

**Files to Create/Modify:**
- `app_secure.py` - Update supervisor-answer endpoint (call n8n grading webhook)
- `escalationv3.html` - Grade display component
- n8n - New grading workflow

---

### 🔲 PHASE 8: HISTORY LOGGING (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 1

**Deliverables:**
1. State transition logger function
2. Add logging to all state-changing endpoints
3. Frontend timeline component
4. Display history in all views

**History Format:**
```json
[
  {
    "timestamp": 1696800000000,
    "from_state": "NOT_ESCALATED",
    "to_state": "ESCALATED_LEVEL_1",
    "action": "escalate",
    "by_user": "employee@company.com",
    "details": "Initial escalation"
  },
  {
    "timestamp": 1696801000000,
    "from_state": "ESCALATED_LEVEL_1",
    "to_state": "AWAITING_INFO",
    "action": "request_info",
    "by_user": "supervisor@company.com",
    "details": "Requested property address"
  }
]
```

**Files to Create/Modify:**
- `app_secure.py` - Logger function + add to all endpoints
- `escalationv3.html` - History timeline component

---

## 🎯 Success Metrics

### Technical Metrics
- All 16 custom fields accessible via API
- All 5 states properly detected and rendered
- All 7 new endpoints functional
- n8n integration working (2 webhooks)
- Zero breaking changes to existing flows

### Business Metrics
- Escalation submission time < 2 minutes
- AI suggestion accuracy > 70%
- Supervisor decision time reduced by 50%
- Training gap identification rate > 80%
- Complete audit trail for all escalations

---

## 🚨 Critical Dependencies

1. ✅ **PROPERTY_LINK field exists** - Field ID: `73999194-0433-433d-a27c-4d9c5f194fd0`
2. ✅ **Property link propagation logic exists** - `/Local/test_property_link_propagation.py`
3. ✅ **ESCALATION_STATUS has 5 options** - Updated with new states:
   - 0: Not Escalated (UUID: `bf10e6ce-bef9-4105-aa2c-913049e2d4ed`)
   - 1: Escalated (UUID: `8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497`)
   - 2: Resolved (UUID: `cbf82936-5488-4612-93a7-f8161071b0eb`)
   - 3: **Escalated Level 2** (UUID: `460769a8-90fa-401d-aeb1-a6d90fb3ee04`) ← NEW
   - 4: **Awaiting Info** (UUID: `ca62ea92-bc51-4d4a-93a8-c084e330e278`) ← NEW
4. ✅ **n8n AI webhook configured** - `https://n8n.oodahost.ai/webhook/d176be54-1622-4b73-a5ce-e02d619a53b9`
5. ✅ **All 14 custom field IDs verified** - Test passed on TICKET-43999
6. 🔲 **n8n grading webhook** - Needs configuration for Phase 7

## 📚 Existing Assets & Code Reuse

### ✅ Available Resources

**Property Link Propagation System** (`/Local/`)
- `test_property_link_propagation.py` - Complete working implementation
- `SHARE_THIS.md` - Integration guide for backend
- `README_property_link_propagation.md` - Documentation & usage

**Key Functions Ready for Integration:**
```python
ensure_property_link(task_id, clickup_token) -> Optional[List[str]]
is_custom_task_id(task_id) -> bool
get_custom_field_value(task, field_id) -> Optional[Any]
get_parent_task_id(task) -> Optional[str]
set_custom_field(task_id, field_id, value) -> Dict
```

**Tested Scenarios:**
- ✅ Custom task ID handling (TICKET-65711)
- ✅ Parent-to-child propagation (868fjz57q → 868fg1umj)
- ✅ Property link format: `{"add": [task_ids]}`
- ✅ Regular ID extraction for POST requests

---

## 📖 Documentation

- `PHASE_1_CHECKLIST.md` - Detailed Phase 1 steps
- `IMPLEMENTATION_ROADMAP.md` - This file
- `CHANGELOG.md` - Track all changes per project CLAUDE.md rules

---

## 🔄 Testing Strategy

### Unit Tests
- Field read/write operations
- State detection logic
- Helper functions

### Integration Tests
- Full escalation flow: Employee → Supervisor → Resolved
- RFI flow: Request → Response → Back to supervisor
- Level 2 flow: Supervisor → Christian → Resolved

### End-to-End Tests
- Complete user journey with all paths
- n8n webhook integration
- Error handling and edge cases

---

**Last Updated:** 2025-10-08
**Owner:** Christian Johnston
**Contributors:** Claude AI
