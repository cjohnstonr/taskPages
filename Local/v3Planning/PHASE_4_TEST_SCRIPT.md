# Phase 4: Test Script

**Created:** 2025-10-08
**Purpose:** Manual testing checklist for Phase 4 (Supervisor Multi-Action UI)

---

## Prerequisites

1. Backend server running (`python app_secure.py`)
2. Logged in with supervisor account
3. Test task ID ready (e.g., TICKET-43999)

---

## Test 1: State Detection (All 5 States)

### Setup
Manually set ESCALATION_STATUS field in ClickUp to each orderindex value.

### Test Cases

| orderIndex | Expected State | Expected UI Component |
|------------|----------------|----------------------|
| 0 | NOT_ESCALATED | EmployeeEscalationForm |
| 1 | ESCALATED | SupervisorActionPanel (3 buttons) |
| 2 | RESOLVED | ResolvedDisplay |
| 3 | ESCALATED_LEVEL_2 | Purple placeholder with "Phase 6" message |
| 4 | AWAITING_INFO | Yellow placeholder with "Phase 5" message |

### Steps
1. Navigate to `/escalation/<task_id>`
2. Open browser console
3. Check: `getDropdownValue()` returns correct state
4. Verify: Correct UI component renders

### Success Criteria
- ✅ All 5 states detected correctly
- ✅ No console errors
- ✅ Appropriate UI renders for each state

---

## Test 2: Supervisor Action Panel (State 1)

### Setup
Set task ESCALATION_STATUS to orderIndex 1 (ESCALATED)

### Test Cases

#### A. Panel Display
- [ ] Red border with "🚨 Escalation Awaiting Your Action" header
- [ ] Employee reason displays correctly
- [ ] AI suggestion displays (if present)
- [ ] 3 buttons visible: Answer / Request Info / Escalate L2

#### B. Button Selection
- [ ] Click "Answer" → Answer form appears
- [ ] Click "Request Info" → RFI form appears
- [ ] Click "Escalate L2" → Level 2 form appears
- [ ] Button highlights when selected (border color changes)

### Success Criteria
- ✅ All UI elements display correctly
- ✅ Button selection works
- ✅ Forms render conditionally

---

## Test 3: Answer Action

### Setup
1. Set task to ESCALATED (orderIndex 1)
2. Navigate to escalation page
3. Click "Answer" button

### Steps
1. Type response in textarea: "This is a test resolution"
2. Click "✅ Submit Answer & Resolve" button
3. Wait for success message
4. Check ClickUp task

### Expected Results

#### Frontend
- [ ] Success alert: "✅ Response submitted successfully!"
- [ ] Page reloads after 1 second

#### ClickUp Fields
- [ ] ESCALATION_RESPONSE_TEXT = "This is a test resolution"
- [ ] ESCALATION_STATUS = 2 (Resolved)
- [ ] ESCALATION_RESOLVED_TIMESTAMP = current timestamp
- [ ] Comment added: "✅ ESCALATION RESOLVED"

#### Backend Logs
```
INFO - Supervisor response for task <task_id> by <email>
INFO - Successfully updated field a077ecc9-1a59-48af-b2cd-42a63f5a7f86
INFO - Successfully updated field 8d784bd0-18e5-4db3-b45e-9a2900262e04
INFO - Successfully updated field c40bf1c4-7d33-4b2b-8765-0784cd88591a
```

### Success Criteria
- ✅ Task transitions to RESOLVED state
- ✅ All fields updated correctly
- ✅ Comment added with resolution details

---

## Test 4: Request Info Action

### Setup
1. Set task to ESCALATED (orderIndex 1)
2. Navigate to escalation page
3. Click "Request Info" button

### Steps
1. Type question in textarea: "What is the exact property address?"
2. Click "❓ Request Information" button
3. Wait for success message
4. Check ClickUp task

### Expected Results

#### Frontend
- [ ] Success alert: "❓ Information requested from employee"
- [ ] Page reloads after 1 second

#### ClickUp Fields
- [ ] ESCALATION_RFI_REQUEST = "What is the exact property address?"
- [ ] ESCALATION_RFI_STATUS = 0 (RFI Requested)
- [ ] ESCALATION_STATUS = 4 (AWAITING_INFO)
- [ ] Comment added: "❓ INFORMATION REQUESTED"

#### Backend Logs
```
INFO - RFI requested for task <task_id> by <email>
INFO - Successfully updated field 0e7dd6f8-3167-4df5-964e-574734ffd4ed
INFO - Successfully updated field f94c0b4b-0c70-4c23-9633-07af2fa6ddc6
INFO - Successfully updated field 8d784bd0-18e5-4db3-b45e-9a2900262e04
```

#### State Transition
- [ ] Task now shows yellow AWAITING_INFO UI
- [ ] RFI question displayed in placeholder
- [ ] "Phase 5" message visible

### Success Criteria
- ✅ Task transitions to AWAITING_INFO state
- ✅ All fields updated correctly
- ✅ Comment added with RFI details
- ✅ State 4 UI renders correctly

---

## Test 5: Escalate to Level 2 Action

### Setup
1. Set task to ESCALATED (orderIndex 1)
2. Navigate to escalation page
3. Click "Escalate L2" button

### Steps
1. Type context in textarea: "Customer is VIP, needs urgent attention"
2. Click "⬆️ Escalate to Level 2" button
3. Wait for success message
4. Check ClickUp task

### Expected Results

#### Frontend
- [ ] Success alert: "⬆️ Escalated to Level 2 (Christian)"
- [ ] Page reloads after 1 second

#### ClickUp Fields
- [ ] ESCALATION_LEVEL = 1 (Christian)
- [ ] ESCALATION_STATUS = 3 (ESCALATED_LEVEL_2)
- [ ] Comment added: "⬆️ ESCALATED TO LEVEL 2 (CHRISTIAN)"
- [ ] Additional context included in comment

#### Backend Logs
```
INFO - Level 2 escalation for task <task_id> by <email>
INFO - Successfully updated field 90d2fec8-7474-4221-84c0-b8c7fb5e4385
INFO - Successfully updated field 8d784bd0-18e5-4db3-b45e-9a2900262e04
```

#### State Transition
- [ ] Task now shows purple ESCALATED_LEVEL_2 UI
- [ ] Original reason displayed
- [ ] AI suggestion displayed (if present)
- [ ] "Phase 6" message visible

### Success Criteria
- ✅ Task transitions to ESCALATED_LEVEL_2 state
- ✅ All fields updated correctly
- ✅ Comment added with escalation details
- ✅ State 3 UI renders correctly

---

## Test 6: Error Handling

### Test Cases

#### A. Empty Response
1. Click "Answer" button
2. Leave textarea empty
3. Click submit
- [ ] Button disabled when textarea empty

#### B. Empty RFI Question
1. Click "Request Info" button
2. Leave textarea empty
3. Click submit
- [ ] Button disabled when textarea empty

#### C. Network Failure
1. Stop backend server
2. Try any action
- [ ] Error alert displays
- [ ] Console shows error message

#### D. Invalid Task ID
1. Navigate to `/escalation/invalid-id`
- [ ] Error page or appropriate error message

### Success Criteria
- ✅ All validation works correctly
- ✅ User-friendly error messages
- ✅ No console errors in valid scenarios

---

## Test 7: Backward Compatibility

### Purpose
Ensure existing Answer flow (from Phase 3) still works unchanged.

### Setup
1. Set task to ESCALATED (orderIndex 1)
2. Use existing Answer button flow

### Steps
1. Click "Answer" button
2. Enter response
3. Submit

### Expected Results
- [ ] Uses `/api/task-helper/supervisor-response/<task_id>` endpoint
- [ ] Updates same fields as before (ESCALATION_RESPONSE_TEXT, ESCALATION_STATUS=2)
- [ ] No breaking changes to existing functionality

### Success Criteria
- ✅ Existing Answer flow works exactly as before
- ✅ No regression in Phase 3 functionality

---

## Test 8: Integration Test (Full Flow)

### Scenario: Employee → Supervisor → RFI → Employee → Supervisor → Resolution

#### Step 1: Employee Escalates
1. Set ESCALATION_STATUS = 0
2. Submit escalation with reason
3. Verify: Status → 1 (ESCALATED)

#### Step 2: Supervisor Requests Info
1. Click "Request Info"
2. Submit question
3. Verify: Status → 4 (AWAITING_INFO)

#### Step 3: Employee Responds (Phase 5 - Placeholder)
- [ ] AWAITING_INFO UI shows RFI question
- [ ] Placeholder message: "Phase 5: RFI response form will be added here"

#### Step 4: Manual Revert to ESCALATED
(Phase 5 will automate this)
1. Manually set ESCALATION_STATUS = 1
2. Verify: SupervisorActionPanel appears again

#### Step 5: Supervisor Resolves
1. Click "Answer"
2. Submit resolution
3. Verify: Status → 2 (RESOLVED)

### Success Criteria
- ✅ State machine works correctly
- ✅ All transitions successful
- ✅ Data persists correctly

---

## Test 9: Performance

### Metrics to Measure

1. **Page Load Time**
   - [ ] < 3 seconds for escalation page

2. **Action Response Time**
   - [ ] Answer action: < 2 seconds
   - [ ] Request Info action: < 2 seconds
   - [ ] Escalate L2 action: < 2 seconds

3. **ClickUp API Calls**
   - [ ] Check network tab: appropriate number of calls
   - [ ] No redundant field updates

### Success Criteria
- ✅ All actions complete within performance targets
- ✅ No performance degradation from Phase 3

---

## Test 10: Security

### Test Cases

#### A. Authentication
1. Log out
2. Try to access `/escalation/<task_id>`
- [ ] Redirects to login

#### B. Rate Limiting
1. Make 15 rapid requests to any endpoint
- [ ] Rate limit kicks in at 10/minute
- [ ] Error message: "Too many requests"

#### C. Input Validation
1. Try XSS in textarea: `<script>alert('xss')</script>`
- [ ] Input sanitized/escaped properly
- [ ] No script execution

### Success Criteria
- ✅ All security measures working
- ✅ No vulnerabilities introduced

---

## Bug Report Template

If you find issues during testing, use this template:

```markdown
### Bug Report

**Test:** [Test number and name]
**Expected:** [What should happen]
**Actual:** [What actually happened]
**Steps to Reproduce:**
1. Step 1
2. Step 2
3. Step 3

**Error Messages:**
```
[Paste error messages here]
```

**Screenshots:** [If applicable]
**Priority:** [High/Medium/Low]
```

---

## Test Summary Template

After completing all tests:

```markdown
## Phase 4 Test Results

**Date:** [Date]
**Tester:** [Name]
**Environment:** [Local/Staging/Production]

### Summary
- ✅ Tests Passed: X/10
- ❌ Tests Failed: X/10
- ⚠️ Issues Found: X

### Critical Issues
1. [Issue 1]
2. [Issue 2]

### Minor Issues
1. [Issue 1]
2. [Issue 2]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]

### Sign-off
- [ ] All critical tests passed
- [ ] No regressions detected
- [ ] Ready for Phase 5 handoff
```

---

## Quick Test Commands

### Set Task to Specific State (via ClickUp UI)
```
State 0 (NOT_ESCALATED): Set dropdown to "Not Escalated"
State 1 (ESCALATED): Set dropdown to "Escalated"
State 2 (RESOLVED): Set dropdown to "Resolved"
State 3 (ESCALATED_LEVEL_2): Set dropdown to "Escalated Level 2"
State 4 (AWAITING_INFO): Set dropdown to "Awaiting Info"
```

### Check Logs
```bash
# Backend logs
tail -f backend.log | grep -E "supervisor-response|request-info|escalate-to-level-2"

# Filter by task ID
tail -f backend.log | grep "TICKET-43999"
```

### Verify ClickUp Fields (API)
```bash
# Get task with custom fields
curl -X GET \
  "https://api.clickup.com/api/v2/task/TICKET-43999" \
  -H "Authorization: YOUR_TOKEN" | jq '.custom_fields'
```

---

## Success Metrics

### Functional
- [ ] 100% state detection accuracy (5/5 states)
- [ ] 0 errors when using supervisor actions
- [ ] 100% ClickUp field update success rate

### Performance
- [ ] < 2 second response time for all actions
- [ ] < 3 second page load for escalation view

### User Experience
- [ ] Supervisor can identify action in < 3 seconds
- [ ] Supervisor can complete action in < 30 seconds
- [ ] Clear error messages for all failure states

---

## Phase 4 Complete Checklist

- [ ] All 10 test scenarios passed
- [ ] No critical bugs
- [ ] Performance targets met
- [ ] Security validated
- [ ] Documentation updated
- [ ] Roadmap updated
- [ ] Phase 5 handoff notes created

---

**Phase 4 Testing Status:** 🔲 Not Started

**Next Steps:**
1. Configure backend environment variables
2. Run this test script
3. Document results
4. Proceed to Phase 5 if all tests pass
