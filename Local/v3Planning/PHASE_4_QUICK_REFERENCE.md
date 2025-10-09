# Phase 4: Quick Reference Card

**For detailed plan, see:** `PHASE_4_DETAILED_PLAN.md`

---

## 🎯 Goal
Transform supervisor response from single "Answer" button into **3-action decision panel**:
- ✅ **Answer** (resolve)
- ❓ **Request Info** (ask employee for more details)
- ⬆️ **Escalate to Level 2** (send to Christian)

---

## 📊 5-State System

| State | Index | UUID | Who Sees |
|-------|-------|------|----------|
| NOT_ESCALATED | 0 | bf10e6ce-bef9-4105-aa2c-913049e2d4ed | Employee |
| ESCALATED | 1 | 8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497 | **Supervisor** ← Phase 4 |
| RESOLVED | 2 | cbf82936-5488-4612-93a7-f8161071b0eb | Everyone |
| ESCALATED_LEVEL_2 | 3 | 460769a8-90fa-401d-aeb1-a6d90fb3ee04 | Christian (Phase 6) |
| AWAITING_INFO | 4 | ca62ea92-bc51-4d4a-93a8-c084e330e278 | Employee (Phase 5) |

---

## 🔧 Implementation Checklist

### Frontend (escalationv3.html)
- [ ] Update `getEscalationStatus()` - add states 3 & 4
- [ ] Create `SupervisorActionPanel` component
- [ ] Add 3-button UI (Answer / Request Info / Escalate L2)
- [ ] Create conditional forms for each action
- [ ] Wire up `handleSupervisorAction()` to backend

### Backend (app_secure.py)
- [ ] Create `/api/task-helper/request-info/<task_id>`
  - Sets: RFI_REQUEST, RFI_STATUS=0, ESCALATION_STATUS=4
- [ ] Create `/api/task-helper/escalate-to-level-2/<task_id>`
  - Sets: ESCALATION_LEVEL=1, ESCALATION_STATUS=3
- [ ] Keep existing `/api/task-helper/supervisor-response/<task_id>`
  - Sets: ESCALATION_RESPONSE_TEXT, ESCALATION_STATUS=2

### Testing
- [ ] Test state detection: all 5 states render correctly
- [ ] Test Answer: resolves to state 2
- [ ] Test Request Info: transitions to state 4
- [ ] Test Escalate L2: transitions to state 3
- [ ] Verify ClickUp field updates
- [ ] Verify comments added

---

## 🚀 Quick Start

### 1. Update State Detection (5 min)
```javascript
const getEscalationStatus = (task) => {
    const statusField = task.custom_fields?.find(f => f.id === FIELD_IDS.ESCALATION_STATUS);
    const orderIndex = statusField?.value;

    if (orderIndex === 0) return 'NOT_ESCALATED';
    if (orderIndex === 1) return 'ESCALATED';
    if (orderIndex === 2) return 'RESOLVED';
    if (orderIndex === 3) return 'ESCALATED_LEVEL_2';  // NEW
    if (orderIndex === 4) return 'AWAITING_INFO';      // NEW

    return 'NOT_ESCALATED';
};
```

### 2. Create SupervisorActionPanel (30 min)
```jsx
function SupervisorActionPanel({ task, onAction }) {
    const [selectedAction, setSelectedAction] = useState(null);

    return (
        <div className="bg-red-50 border-2 border-red-600 rounded-lg p-6">
            {/* 3-button selection */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <button onClick={() => setSelectedAction('answer')}>✅ Answer</button>
                <button onClick={() => setSelectedAction('request-info')}>❓ Request Info</button>
                <button onClick={() => setSelectedAction('escalate-level-2')}>⬆️ Escalate L2</button>
            </div>

            {/* Dynamic forms based on selection */}
            {selectedAction === 'answer' && <AnswerForm onSubmit={onAction} />}
            {selectedAction === 'request-info' && <RequestInfoForm onSubmit={onAction} />}
            {selectedAction === 'escalate-level-2' && <EscalateLevel2Form onSubmit={onAction} />}
        </div>
    );
}
```

### 3. Add Backend Endpoints (20 min)
```python
# Endpoint 1: Request Info
@app.route('/api/task-helper/request-info/<task_id>', methods=['POST'])
@login_required
def request_info(task_id):
    data = request.get_json()
    question = data.get('question')

    # Update fields: RFI_REQUEST, RFI_STATUS=0, ESCALATION_STATUS=4
    # Add comment
    return jsonify({"success": True})

# Endpoint 2: Escalate to Level 2
@app.route('/api/task-helper/escalate-to-level-2/<task_id>', methods=['POST'])
@login_required
def escalate_to_level_2(task_id):
    data = request.get_json()
    context = data.get('context')

    # Update fields: ESCALATION_LEVEL=1, ESCALATION_STATUS=3
    # Add comment
    return jsonify({"success": True})
```

---

## 🧪 Test Commands

### Test State Detection
```javascript
// In browser console
const task = window.taskData; // Assuming task data is available
console.log('Current state:', getEscalationStatus(task));
```

### Test Actions (Manual)
1. **Setup:** Set TICKET-43999 to ESCALATION_STATUS = 1 (Escalated)
2. **Navigate:** Go to `/escalation/TICKET-43999`
3. **Test Each Action:**
   - Click "Answer" → Should show answer form
   - Click "Request Info" → Should show RFI form
   - Click "Escalate L2" → Should show L2 form
4. **Verify:** Each submission updates ClickUp correctly

---

## 📋 Phase Handoffs

### Phase 4 → Phase 5 (RFI System)
**What Phase 4 Delivers:**
- ✅ AWAITING_INFO state (4) detection
- ✅ Request Info button and form
- ✅ `/api/task-helper/request-info/<task_id>` endpoint
- ✅ RFI_REQUEST field populated

**What Phase 5 Must Build:**
- 🔲 RFI response form for employees
- 🔲 `/api/task-helper/respond-to-rfi/<task_id>` endpoint
- 🔲 State transition: AWAITING_INFO → ESCALATED
- 🔲 RFI_RESPONSE field handling

### Phase 4 → Phase 6 (Level 2)
**What Phase 4 Delivers:**
- ✅ ESCALATED_LEVEL_2 state (3) detection
- ✅ Escalate L2 button and form
- ✅ `/api/task-helper/escalate-to-level-2/<task_id>` endpoint
- ✅ ESCALATION_LEVEL field set to 1 (Christian)

**What Phase 6 Must Build:**
- 🔲 Christian action panel UI
- 🔲 `/api/task-helper/christian-answer/<task_id>` endpoint
- 🔲 State transition: ESCALATED_LEVEL_2 → RESOLVED
- 🔲 Christian-specific permissions/routing

---

## ⏱️ Time Estimates

| Task | Time | Priority |
|------|------|----------|
| Update state detection | 30 min | HIGH |
| Create SupervisorActionPanel | 2 hours | HIGH |
| Create backend endpoints | 2 hours | HIGH |
| Update EscalationModule rendering | 1 hour | MEDIUM |
| Wire frontend to backend | 1 hour | MEDIUM |
| Testing & validation | 1.5 hours | HIGH |
| Documentation | 30 min | LOW |

**Total: ~8 hours (1 day)**

---

## 🔍 Debug Checklist

**If state not detected:**
- [ ] Verify orderIndex value in ClickUp
- [ ] Check FIELD_IDS.ESCALATION_STATUS is correct
- [ ] Console.log the statusField value
- [ ] Ensure getEscalationStatus handles undefined gracefully

**If button doesn't work:**
- [ ] Check network tab for endpoint call
- [ ] Verify backend endpoint exists and is running
- [ ] Check CORS/authentication issues
- [ ] Ensure request body format matches backend expectation

**If ClickUp not updating:**
- [ ] Verify field IDs are correct
- [ ] Check API token permissions
- [ ] Ensure using regular task ID (not custom ID) for POST
- [ ] Check backend logs for field update errors

---

## 📄 Related Documents

- **Detailed Plan:** `PHASE_4_DETAILED_PLAN.md` (full architecture, code samples, testing)
- **Roadmap:** `IMPLEMENTATION_ROADMAP_v2.md` (overall project status)
- **Phase 3 Reference:** `test_phase3_n8n_integration.py` (previous phase completion)
- **Field IDs:** `ESCALATION_FIELDS_ACTUAL.md` (all custom field mappings)
