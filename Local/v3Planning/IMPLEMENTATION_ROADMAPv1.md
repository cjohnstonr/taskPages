# Escalation System v3 - Implementation Roadmap

**Project:** Advanced Escalation System with AI Integration
**Status:** Phase 1 - Foundation
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
| 1 | Foundation | 1 day | 🟡 IN PROGRESS | Everything |
| 2 | Property Link Validation | 1 day | ⏸️ WAITING | n8n integration |
| 3 | n8n AI Suggestion | 2 days | ⏸️ WAITING | AI features |
| 4 | Supervisor Multi-Action UI | 1 day | ⏸️ WAITING | Routing |
| 5 | RFI System | 1 day | ⏸️ WAITING | Info requests |
| 6 | Level 2 Escalation | 1 day | ⏸️ WAITING | Christian queue |
| 7 | AI Grading | 1 day | ⏸️ WAITING | Analysis |
| 8 | History Logging | 1 day | ⏸️ WAITING | Audit trail |

**Total Estimated Time:** 9 days

---

## 📋 Implementation Phases

### ✅ PHASE 1: FOUNDATION (1 DAY)
**Status:** 🟡 IN PROGRESS

**Deliverables:**
1. ✅ 8 existing custom fields verified
2. 🔲 ESCALATION_STATUS dropdown updated (add 2 new options)
3. 🔲 8 new custom fields created in ClickUp
4. ✅ Frontend constants updated with field IDs
5. ✅ Backend constants updated with field IDs
6. 🔲 All UUIDs filled in (no TODO markers)
7. 🔲 Verification tests passed

**Files Modified:**
- `escalation-v2.html` (lines 210-218)
- `app_secure.py` (lines 740-748)

**Checklist:** See `PHASE_1_CHECKLIST.md`

---

### 🔲 PHASE 2: PROPERTY LINK VALIDATION (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 1

**Deliverables:**
1. Property link extraction logic (check task → check parent)
2. Property link auto-copy to subtask if missing
3. Pre-escalation validation endpoint: `/api/task-helper/validate-property-link/<task_id>`
4. Frontend validator component (blocks escalation if no property link)
5. Error UI: "This task must have a property link"

**Why Critical:**
- n8n needs property link to fetch context
- Vector store selection depends on property
- Cannot proceed to Phase 3 without this

**Files to Create/Modify:**
- `app_secure.py` - New endpoint
- `escalation-v2.html` - Validator component

---

### 🔲 PHASE 3: n8n AI SUGGESTION (2 DAYS)
**Status:** ⏸️ WAITING FOR PHASE 2

**Deliverables:**
1. n8n webhook: `/webhook/escalation-ai-analysis`
2. New backend endpoint: `/api/task-helper/escalate-with-ai/<task_id>`
3. n8n receives: task_id + property_link
4. n8n returns: AI suggestion based on SOPs
5. Save to: `AI_SUGGESTION` + `AI_SOLUTION_DISPLAY`
6. Frontend component: Display AI suggestion to employee

**n8n Workflow Steps:**
1. Receive task_id + property_link
2. Fetch full task tree from ClickUp API
3. Query property-specific vector store
4. Analyze against SOPs
5. Generate suggested solution
6. Return JSON: `{ai_suggestion: "text"}`

**Files to Create/Modify:**
- `app_secure.py` - Replace `/escalate` with `/escalate-with-ai`
- `escalation-v2.html` - AI suggestion display component
- n8n - New workflow

---

### 🔲 PHASE 4: SUPERVISOR MULTI-ACTION UI (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 1

**Deliverables:**
1. State detection for AWAITING_INFO (3) and ESCALATED_LEVEL_2 (4)
2. Supervisor action panel component (3 buttons)
3. Backend endpoint: `/api/task-helper/supervisor-answer/<task_id>`
4. Backend endpoint: `/api/task-helper/request-info/<task_id>`
5. Backend endpoint: `/api/task-helper/escalate-to-level-2/<task_id>`

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

**Files to Create/Modify:**
- `escalation-v2.html` - Action panel component
- `app_secure.py` - 3 new endpoints

---

### 🔲 PHASE 5: RFI SYSTEM (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 4

**Deliverables:**
1. RFI request form (supervisor enters what info needed)
2. AWAITING_INFO state UI (employee sees request)
3. RFI response form (employee responds)
4. Backend endpoint: `/api/task-helper/respond-to-rfi/<task_id>`
5. State transition: AWAITING_INFO → ESCALATED_LEVEL_1

**Flow:**
```
Supervisor clicks "Request Info"
    ↓
Enters: "What is the property address?"
    ↓
ESCALATION_STATUS = 3 (Awaiting Info)
RFI_REQUEST = "What is the property address?"
    ↓
Employee sees RFI request
    ↓
Employee responds: "123 Main St"
    ↓
RFI_RESPONSE = "123 Main St"
ESCALATION_STATUS = 1 (back to supervisor)
```

**Files to Create/Modify:**
- `escalation-v2.html` - RFI components
- `app_secure.py` - RFI response endpoint

---

### 🔲 PHASE 6: LEVEL 2 ESCALATION (1 DAY)
**Status:** ⏸️ WAITING FOR PHASE 4

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
- `escalation-v2.html` - Level 2 components
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
- `app_secure.py` - Update supervisor-answer endpoint
- `escalation-v2.html` - Grade display component
- n8n - New workflow

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
- `escalation-v2.html` - History timeline component

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

1. **PROPERTY_LINK field MUST exist** before Phase 3
2. **ESCALATION_STATUS MUST have 5 options** before Phase 4
3. **n8n webhooks MUST be configured** before Phase 3 & 7
4. **All custom field UUIDs MUST be filled** before any phase

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
