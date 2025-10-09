# Escalation System v3 - MASTER IMPLEMENTATION PLAN

**Project:** AI-Powered Multi-Level Escalation System
**Status:** Phase 1 Complete, Ready for Phase 2
**Last Updated:** 2025-10-08
**Owner:** Christian Johnston

---

## 🎯 PROJECT VISION

Transform current 3-state escalation into comprehensive AI-powered workflow:
- **Property-aware context** via vector stores
- **AI suggestions** from n8n analyzing SOPs
- **Multi-level routing:** Shirley (L1) → Christian (L2)
- **RFI capability:** Supervisors can request more info
- **AI grading:** Evaluate human responses vs AI suggestions
- **Complete audit trail:** JSON history of all transitions

---

## 📊 CRITICAL CONTEXT FROM CONVERSATION

### **What Christian Explained:**

1. **Property Link is Essential:**
   - Links escalation to specific property
   - Enables property-specific AI vector store queries
   - Must be on task OR parent task
   - If missing on subtask, copy from parent BEFORE sending to n8n

2. **n8n Integration Flow:**
   - Send task_id + property_link to n8n
   - n8n fetches full task tree from ClickUp
   - n8n queries property vector store + SOPs
   - n8n returns AI suggestion
   - No need to send task tree from backend (n8n does it)

3. **RFI Simplification:**
   - Only 3 states: None (null), RFI Requested (0), RFI Completed (1)
   - RFI_STATUS works alongside ESCALATION_STATUS (not replacing it)
   - Can happen at any escalation level (L1 or L2)

4. **Escalation Levels:**
   - Level 0 = Shirley (supervisor)
   - Level 1 = Christian (final level)
   - NOT generic "supervisor" - actual names used

5. **AI Suggestion Field:**
   - ONE field serves both purposes: `ESCALATION_AI_SUGGESTION`
   - Stores what n8n returns
   - Displays to employee
   - NO separate display field needed

---

## ✅ PHASE 1 - COMPLETE

### All 13 Fields Exist in ClickUp:

```javascript
// ACTUAL FIELD IDS FROM CLICKUP
ESCALATION_REASON_TEXT: 'c6e0281e-9001-42d7-a265-8f5da6b71132'
ESCALATION_REASON_AI: 'e9e831f2-b439-4067-8e88-6b715f4263b2'
ESCALATION_AI_SUGGESTION: 'bc5e9359-01cd-408f-adb9-c7bdf1f2dd29'
ESCALATION_STATUS: '8d784bd0-18e5-4db3-b45e-9a2900262e04'
ESCALATION_SUBMITTED_DATE_TIME: '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f'
ESCALATION_RESPONSE_TEXT: 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86'
ESCALATION_RESOLVED_DATE_TIME: 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
ESCALATION_AI_GRADE: '629ca244-a6d3-46dd-9f1e-6a0ded40f519'
ESCALATION_HISTORY: '94790367-5d1f-4300-8f79-e13819f910d4'
ESCALATION_LEVEL: '90d2fec8-7474-4221-84c0-b8c7fb5e4385' // Note: Field name typo "Esclation"
ESCALATION_RFI_STATUS: 'f94c0b4b-0c70-4c23-9633-07af2fa6ddc6'
ESCALATION_RFI_REQUEST: '0e7dd6f8-3167-4df5-964e-574734ffd4ed'
ESCALATION_RFI_RESPONSE: 'b5c52661-8142-45e0-bec5-14f3c135edbc'
```

### Dropdown Configurations (WITH UUIDs):

**ESCALATION_STATUS:**
- Order 0 = "Not Escalated" (UUID: `bf10e6ce-bef9-4105-aa2c-913049e2d4ed`)
- Order 1 = "Escalated" (UUID: `8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497`)
- Order 2 = "Resolved" (UUID: `cbf82936-5488-4612-93a7-f8161071b0eb`)

**ESCALATION_LEVEL:**
- Order 0 = "Shirley" (UUID: `cfd3a04c-5b0c-4ddd-b65e-df65bd662ef5`)
- Order 1 = "Christian" (UUID: `841566bc-4076-433e-af7b-9b5214bdc991`)

**ESCALATION_RFI_STATUS:**
- Order 0 = "RFI Requested" (UUID: `9b404ea6-efb7-40d1-9820-75ed5f5f47ff`)
- Order 1 = "RFI Completed" (UUID: `3e28b07a-361a-4fc8-bc78-0d8774167939`)
- **NO "None" option** → Use `null` for "no RFI active"

### Code Updates Made:
- ✅ `escalation-v2.html` lines 200-216 (all UUIDs filled)
- ✅ `app_secure.py` lines 730-747 (all UUIDs filled)

---

## ⚠️ CRITICAL ISSUES & DECISIONS

### Issue 1: RFI_STATUS Has No "None" Option

**Decision:** Use `null` to represent "no RFI active"

**Implementation Pattern:**
```javascript
function getRFIStatus(task) {
    const field = task.custom_fields.find(f => f.id === FIELD_IDS.ESCALATION_RFI_STATUS);
    if (!field || field.value === null || field.value === undefined) {
        return null; // No RFI active
    }
    return field.value; // 0 = Requested, 1 = Completed
}

// When setting RFI status:
// To activate RFI: Set value to 0 (RFI Requested)
// To complete RFI: Set value to 1 (RFI Completed)
// To clear RFI: Set value to null (use ClickUp API field update with null)
```

### Issue 2: PROPERTY_LINK Field Missing

**Status:** NOT in ClickUp fields export

**CRITICAL BLOCKER:** Cannot proceed to Phase 3 (n8n) without this

**Action Required:**
1. Search ClickUp for existing "Property" or "Property Link" field
2. If exists, get UUID and update constants
3. If not exists, create new Task Relationship field named "Property_Link"
4. Update both `escalation-v2.html` and `app_secure.py` constants

**Current Placeholder:** `PROPERTY_LINK: 'TODO_FIND_IN_CLICKUP'`

**Note from CLAUDE.md:** There IS property link propagation logic already (`/Local/test_property_link_propagation.py`), so field likely exists - just need to find UUID

---

## 🎯 COMPLETE STATE MACHINE

### State Detection Logic:

```javascript
function determineEscalationState(task) {
    const status = getCustomField(task, FIELD_IDS.ESCALATION_STATUS); // 0, 1, or 2
    const level = getCustomField(task, FIELD_IDS.ESCALATION_LEVEL); // 0 or 1
    const rfiStatus = getCustomField(task, FIELD_IDS.ESCALATION_RFI_STATUS); // null, 0, or 1

    // PRIMARY STATE
    if (status === 0) return 'NOT_ESCALATED';
    if (status === 2) return 'RESOLVED';

    // ESCALATED STATE (status === 1)
    // Check level and RFI sub-states

    const isShirley = (level === 0 || level === null); // Default to Shirley if not set
    const isChristian = (level === 1);

    if (rfiStatus === null) {
        // No RFI active - normal escalated state
        return isShirley ? 'ESCALATED_SHIRLEY' : 'ESCALATED_CHRISTIAN';
    }
    else if (rfiStatus === 0) {
        // RFI Requested - awaiting employee response
        return isShirley ? 'ESCALATED_SHIRLEY_RFI_REQUESTED' : 'ESCALATED_CHRISTIAN_RFI_REQUESTED';
    }
    else if (rfiStatus === 1) {
        // RFI Completed - supervisor reviewing employee's response
        return isShirley ? 'ESCALATED_SHIRLEY_RFI_COMPLETED' : 'ESCALATED_CHRISTIAN_RFI_COMPLETED';
    }
}
```

### State Transition Flows:

**Flow 1: Direct Answer (No RFI)**
```
NOT_ESCALATED (status=0)
    ↓ Employee escalates
ESCALATED_SHIRLEY (status=1, level=0, rfi=null)
    ↓ Shirley answers
RESOLVED (status=2)
```

**Flow 2: RFI Request → Response → Answer**
```
ESCALATED_SHIRLEY (status=1, level=0, rfi=null)
    ↓ Shirley requests info
ESCALATED_SHIRLEY_RFI_REQUESTED (status=1, level=0, rfi=0)
    ↓ Employee responds
ESCALATED_SHIRLEY_RFI_COMPLETED (status=1, level=0, rfi=1)
    ↓ Shirley reviews and answers
RESOLVED (status=2)
```

**Flow 3: Escalate to Christian**
```
ESCALATED_SHIRLEY (status=1, level=0, rfi=null)
    ↓ Shirley escalates
ESCALATED_CHRISTIAN (status=1, level=1, rfi=null)
    ↓ Christian can RFI or answer
RESOLVED (status=2)
```

**Flow 4: Multiple RFI Rounds**
```
ESCALATED_SHIRLEY_RFI_COMPLETED (status=1, level=0, rfi=1)
    ↓ Shirley needs MORE info
ESCALATED_SHIRLEY_RFI_REQUESTED (status=1, level=0, rfi=0) ← Reset to Requested
    ↓ Employee responds again
ESCALATED_SHIRLEY_RFI_COMPLETED (status=1, level=0, rfi=1)
```

---

## 📋 8-PHASE IMPLEMENTATION PLAN

### ✅ PHASE 1: FOUNDATION - **COMPLETE**
- All field IDs mapped
- Code constants updated
- Dropdown UUIDs documented

### 🔲 PHASE 2: PROPERTY LINK VALIDATION - **NEXT**

**Goal:** Ensure property_link exists before escalation, copy from parent if needed

**Deliverables:**
1. Find PROPERTY_LINK field UUID in ClickUp
2. Backend endpoint: `GET /api/task-helper/validate-property-link/<task_id>`
   - Check if property_link exists on task
   - If not, check parent task
   - If parent has it, copy to subtask
   - Return validation result
3. Frontend pre-escalation validator
4. Error UI if no property link found

**Critical Logic:**
```python
def validate_and_copy_property_link(task_id):
    # 1. Get task
    task = clickup_api.get_task(task_id)

    # 2. Check if task has property_link
    property_link = get_custom_field(task, PROPERTY_LINK_FIELD_ID)
    if property_link:
        return {"valid": True, "property_link": property_link}

    # 3. Get parent task
    parent_id = task.get('parent')
    if not parent_id:
        return {"valid": False, "error": "No property link and no parent"}

    parent = clickup_api.get_task(parent_id)
    parent_property_link = get_custom_field(parent, PROPERTY_LINK_FIELD_ID)

    if not parent_property_link:
        return {"valid": False, "error": "No property link on task or parent"}

    # 4. Copy property link to subtask
    clickup_api.set_custom_field(task_id, PROPERTY_LINK_FIELD_ID, parent_property_link)

    return {"valid": True, "property_link": parent_property_link, "copied_from_parent": True}
```

**Files to Modify:**
- `app_secure.py` - New endpoint
- `escalation-v2.html` - Pre-escalation check component

---

### 🔲 PHASE 3: n8n AI SUGGESTION INTEGRATION

**Goal:** Get AI-suggested solutions from n8n based on property context

**n8n Webhook:** `/webhook/escalation-ai-analysis`

**Input to n8n:**
```json
{
  "task_id": "abc123",
  "property_link": "task_uuid_of_property"
}
```

**n8n Workflow:**
1. Receive task_id + property_link
2. Fetch full task tree from ClickUp API (n8n does this, not backend)
3. Query property-specific vector store using property_link
4. Analyze task context against SOPs
5. Generate AI suggestion
6. Return JSON

**Output from n8n:**
```json
{
  "ai_suggestion": "Based on the task context and property SOPs, here's how to resolve..."
}
```

**Backend Endpoint:** `POST /api/task-helper/escalate-with-ai/<task_id>`

**Flow:**
```python
def escalate_with_ai(task_id):
    # 1. Validate property link (Phase 2 function)
    validation = validate_and_copy_property_link(task_id)
    if not validation['valid']:
        return error("Property link required")

    # 2. Get escalation reason from request
    reason = request.json.get('reason')
    ai_summary = request.json.get('ai_summary', '')

    # 3. Call n8n webhook
    n8n_response = requests.post(N8N_WEBHOOK_URL, json={
        "task_id": task_id,
        "property_link": validation['property_link']
    })
    ai_suggestion = n8n_response.json().get('ai_suggestion')

    # 4. Update ClickUp fields
    update_fields = [
        (FIELD_IDS.ESCALATION_REASON_TEXT, reason),
        (FIELD_IDS.ESCALATION_REASON_AI, ai_summary),
        (FIELD_IDS.ESCALATION_AI_SUGGESTION, ai_suggestion),  # From n8n
        (FIELD_IDS.ESCALATION_STATUS, 1),  # Escalated
        (FIELD_IDS.ESCALATION_LEVEL, 0),  # Shirley
        (FIELD_IDS.ESCALATION_SUBMITTED_DATE_TIME, timestamp),
        (FIELD_IDS.ESCALATION_RFI_STATUS, None)  # Clear any previous RFI
    ]

    for field_id, value in update_fields:
        clickup_api.set_field(task_id, field_id, value)

    return success()
```

**Frontend Changes:**
- Display AI suggestion to employee after escalation
- Show in new component: `<AISuggestionDisplay suggestion={aiSuggestion} />`

---

### 🔲 PHASE 4: SUPERVISOR MULTI-ACTION UI

**Goal:** Shirley sees 3 options: Answer / Request Info / Escalate to Christian

**UI Component:**
```jsx
<SupervisorActionPanel>
  <button onClick={handleAnswer}>✅ Answer</button>
  <button onClick={handleRequestInfo}>❓ Request Info</button>
  <button onClick={handleEscalateToChristian}>⬆️ Escalate to Christian</button>
</SupervisorActionPanel>
```

**Backend Endpoints:**

1. **`POST /api/task-helper/supervisor-answer/<task_id>`**
   - Input: `{answer: "text"}`
   - Updates: ESCALATION_RESPONSE_TEXT, ESCALATION_STATUS=2, ESCALATION_RESOLVED_DATE_TIME
   - Calls n8n for grading (Phase 7)

2. **`POST /api/task-helper/request-info/<task_id>`**
   - Input: `{info_request: "What is the property address?"}`
   - Updates: ESCALATION_RFI_STATUS=0, ESCALATION_RFI_REQUEST=text

3. **`POST /api/task-helper/escalate-to-christian/<task_id>`**
   - Input: `{additional_context: "optional"}`
   - Updates: ESCALATION_LEVEL=1, ESCALATION_RFI_STATUS=null (reset RFI)

---

### 🔲 PHASE 5: RFI SYSTEM

**Employee RFI Response UI:**
```jsx
// When ESCALATION_RFI_STATUS === 0 (Requested)
<RFIResponseForm>
  <p>Supervisor requested: {rfiRequest}</p>
  <textarea value={rfiResponse} onChange={setRFIResponse} />
  <button onClick={submitRFIResponse}>Submit Response</button>
</RFIResponseForm>
```

**Backend Endpoint:**
- **`POST /api/task-helper/respond-to-rfi/<task_id>`**
  - Input: `{rfi_response: "123 Main St, Unit 5B"}`
  - Updates: ESCALATION_RFI_STATUS=1, ESCALATION_RFI_RESPONSE=text

**Supervisor sees:**
```jsx
// When ESCALATION_RFI_STATUS === 1 (Completed)
<RFICompletedView>
  <p>You requested: {rfiRequest}</p>
  <p>Employee responded: {rfiResponse}</p>
  <SupervisorActionPanel /> // Can answer/request-more/escalate
</RFICompletedView>
```

---

### 🔲 PHASE 6: LEVEL 2 ESCALATION (CHRISTIAN)

**Christian's View:**
- Same UI as Shirley's
- Can: Answer, Request Info (RFI)
- Cannot: Escalate further (already at top level)

**Backend Endpoint:**
- **`POST /api/task-helper/christian-answer/<task_id>`**
  - Same as supervisor-answer
  - Updates: ESCALATION_RESPONSE_TEXT, ESCALATION_STATUS=2

---

### 🔲 PHASE 7: AI GRADING

**n8n Webhook:** `/webhook/grade-response`

**Input to n8n:**
```json
{
  "task_id": "abc123",
  "supervisor_answer": "text",
  "ai_suggestion": "text from Phase 3"
}
```

**Output from n8n:**
```json
{
  "grade": "The supervisor's answer aligns well with SOPs...",
  "feedback": "Consider mentioning X for completeness"
}
```

**Integration:**
- Called from `supervisor-answer` or `christian-answer` endpoints
- Saved to ESCALATION_AI_GRADE field
- Displayed in resolved view

---

### 🔲 PHASE 8: HISTORY LOGGING

**Field:** ESCALATION_HISTORY (JSON array)

**Format:**
```json
[
  {
    "timestamp": 1696800000000,
    "from_state": "NOT_ESCALATED",
    "to_state": "ESCALATED_SHIRLEY",
    "action": "escalate",
    "by_user": "employee@example.com"
  },
  {
    "timestamp": 1696801000000,
    "from_state": "ESCALATED_SHIRLEY",
    "to_state": "ESCALATED_SHIRLEY_RFI_REQUESTED",
    "action": "request_info",
    "by_user": "shirley@example.com",
    "details": "Requested property address"
  }
]
```

**Logger Function:**
```python
def log_state_transition(task_id, from_state, to_state, action, user, details=None):
    # Get current history
    task = clickup_api.get_task(task_id)
    history = get_custom_field(task, FIELD_IDS.ESCALATION_HISTORY)
    history = json.loads(history) if history else []

    # Append new entry
    history.append({
        "timestamp": int(datetime.now().timestamp() * 1000),
        "from_state": from_state,
        "to_state": to_state,
        "action": action,
        "by_user": user,
        "details": details
    })

    # Save back
    clickup_api.set_field(task_id, FIELD_IDS.ESCALATION_HISTORY, json.dumps(history))
```

**Call from every state-changing endpoint**

---

## 🚨 CRITICAL REMINDERS

1. **PROPERTY_LINK is BLOCKER** - Must find/create before Phase 3
2. **RFI_STATUS uses null for "None"** - Never set to 0 unless actually requesting info
3. **Field names differ from assumptions** - Use ESCALATION_REASON_TEXT not ESCALATION_REASON
4. **n8n fetches task tree** - Don't send full context from backend, just task_id + property_link
5. **ESCALATION_AI_SUGGESTION serves both purposes** - Store AND display, no separate field
6. **Levels use actual names** - "Shirley" and "Christian", not generic labels

---

## 📁 FILES CREATED

- `ESCALATION_V3_MASTER_PLAN.md` ← THIS FILE (complete reference)
- `ESCALATION_FIELDS_ACTUAL.md` (field reference with UUIDs)
- `PHASE_1_COMPLETE.md` (Phase 1 summary)
- `IMPLEMENTATION_ROADMAP.md` (original 8-phase plan)
- `PHASE_1_CHECKLIST.md` (deprecated - replaced by PHASE_1_COMPLETE.md)

**Code Files Modified:**
- `escalation-v2.html` lines 200-216
- `app_secure.py` lines 730-747

---

## 🎯 IMMEDIATE NEXT STEPS

1. **Find PROPERTY_LINK field UUID** (check ClickUp or ask Christian)
2. **Update constants** in both files with PROPERTY_LINK UUID
3. **Begin Phase 2** implementation (property link validation)
4. **Test Phase 2** endpoint before moving to Phase 3

---

**Last Updated:** 2025-10-08
**Context Preserved For:** AI continuation or project handoff
