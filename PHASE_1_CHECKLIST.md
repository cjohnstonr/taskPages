# PHASE 1: FOUNDATION - Custom Fields Setup

**Status:** 🟡 IN PROGRESS
**Started:** 2025-10-08
**Estimated Completion:** 1 day

---

## ✅ COMPLETED

### 1. Existing Fields Verified (8 fields)

| Field Name | Field ID | Type | Status |
|------------|----------|------|--------|
| ESCALATION_REASON | `c6e0281e-9001-42d7-a265-8f5da6b71132` | Text | ✅ EXISTS |
| ESCALATION_AI_SUMMARY | `e9e831f2-b439-4067-8e88-6b715f4263b2` | Text | ✅ EXISTS |
| ESCALATION_AI_SUGGESTION | `bc5e9359-01cd-408f-adb9-c7bdf1f2dd29` | Text | ✅ EXISTS |
| ESCALATION_STATUS | `8d784bd0-18e5-4db3-b45e-9a2900262e04` | Dropdown | ✅ EXISTS |
| ESCALATED_TO | `934811f1-239f-4d53-880c-3655571fd02e` | Text | ✅ EXISTS |
| ESCALATION_TIMESTAMP | `5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f` | Date | ✅ EXISTS |
| SUPERVISOR_RESPONSE | `a077ecc9-1a59-48af-b2cd-42a63f5a7f86` | Text | ✅ EXISTS |
| ESCALATION_RESOLVED_TIMESTAMP | `c40bf1c4-7d33-4b2b-8765-0784cd88591a` | Date | ✅ EXISTS |

### 2. Code Updated

- ✅ Frontend constants updated: `escalation-v2.html:210-218`
- ✅ Backend constants updated: `app_secure.py:740-748`

---

## 🔲 TODO

### STEP 1: Update ESCALATION_STATUS Dropdown

**Field:** ESCALATION_STATUS (`8d784bd0-18e5-4db3-b45e-9a2900262e04`)

**Current Options:**
- 0 = "Not Escalated"
- 1 = "Escalated"
- 2 = "Resolved"

**ADD These Options in ClickUp:**
- [ ] Add option 3: **"Awaiting Info"** (for RFI state)
- [ ] Add option 4: **"Escalated Level 2"** (for Christian's queue)

**How to do this:**
1. Go to ClickUp → Settings → Custom Fields
2. Find "Escalation Status" dropdown field
3. Click "Edit Field"
4. Add new options: "Awaiting Info" and "Escalated Level 2"
5. Save

---

### STEP 2: Check if PROPERTY_LINK Field Exists

**Action:**
- [ ] Search ClickUp custom fields for "Property" or "Property Link"
- [ ] If exists, get UUID and update code constants
- [ ] If NOT exists, create new field (see STEP 3)

**Where to check:**
- ClickUp → Settings → Custom Fields → Process Library list

---

### STEP 3: Create NEW Custom Fields in ClickUp

Create these 7 new fields (or 6 if PROPERTY_LINK already exists):

#### Field 1: PROPERTY_LINK (if doesn't exist)
- [ ] Name: **Property Link**
- [ ] Type: **Task Relationship**
- [ ] Required: **Yes** (enforce in code, not ClickUp)
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 2: AI_GRADE_OF_RESPONSE
- [ ] Name: **AI Grade of Response**
- [ ] Type: **Long Text**
- [ ] Default: Empty
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 3: ESCALATION_LEVEL
- [ ] Name: **Escalation Level**
- [ ] Type: **Dropdown**
- [ ] Options:
  - 1 = "Supervisor" (default)
  - 2 = "Christian"
- [ ] Default: 1 (Supervisor)
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 4: RFI_STATUS
- [ ] Name: **RFI Status**
- [ ] Type: **Dropdown**
- [ ] Options:
  - 0 = "None" (default)
  - 1 = "Active"
  - 2 = "Responded"
  - 3 = "Resolved"
- [ ] Default: 0 (None)
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 5: RFI_REQUEST
- [ ] Name: **RFI Request**
- [ ] Type: **Long Text**
- [ ] Default: Empty
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 6: RFI_RESPONSE
- [ ] Name: **RFI Response**
- [ ] Type: **Long Text**
- [ ] Default: Empty
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

#### Field 7: ESCALATION_HISTORY
- [ ] Name: **Escalation History**
- [ ] Type: **Long Text**
- [ ] Default: `[]` (empty JSON array)
- [ ] Purpose: Stores JSON log of state transitions
- [ ] Location: Process Library task list
- [ ] After creation, copy UUID → Update code constants

---

### STEP 4: Update Code Constants with New UUIDs

After creating fields in ClickUp, update these files:

**File 1: escalation-v2.html**
- [ ] Replace `PROPERTY_LINK: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 211)
- [ ] Replace `AI_GRADE_OF_RESPONSE: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 212)
- [ ] Replace `ESCALATION_LEVEL: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 213)
- [ ] Replace `RFI_STATUS: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 214)
- [ ] Replace `RFI_REQUEST: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 215)
- [ ] Replace `RFI_RESPONSE: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 216)
- [ ] Replace `ESCALATION_HISTORY: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 217)

**File 2: app_secure.py**
- [ ] Replace `PROPERTY_LINK: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 741)
- [ ] Replace `AI_GRADE_OF_RESPONSE: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 742)
- [ ] Replace `ESCALATION_LEVEL: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 743)
- [ ] Replace `RFI_STATUS: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 744)
- [ ] Replace `RFI_REQUEST: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 745)
- [ ] Replace `RFI_RESPONSE: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 746)
- [ ] Replace `ESCALATION_HISTORY: 'TODO_GET_FROM_CLICKUP'` with actual UUID (line 747)

---

### STEP 5: Verification Testing

After all fields are created and UUIDs updated:

#### Test 1: Field Read Access
- [ ] Create test script to read all fields from a Process Library task
- [ ] Verify all 16 escalation fields can be accessed via ClickUp API
- [ ] Verify field types match expectations (dropdown vs text vs date)

#### Test 2: Field Write Access
- [ ] Test writing to each new field via ClickUp API
- [ ] Verify values save correctly
- [ ] Verify dropdown fields accept correct orderindex values

#### Test 3: Frontend Access
- [ ] Load escalation-v2.html with a test task
- [ ] Check browser console for errors about missing field IDs
- [ ] Verify `getCustomField(task, FIELD_IDS.PROPERTY_LINK)` returns data

---

## 📋 QUICK REFERENCE: All Field IDs

### Existing Fields (8)
```javascript
ESCALATION_REASON: 'c6e0281e-9001-42d7-a265-8f5da6b71132'
ESCALATION_AI_SUMMARY: 'e9e831f2-b439-4067-8e88-6b715f4263b2'
ESCALATION_AI_SUGGESTION: 'bc5e9359-01cd-408f-adb9-c7bdf1f2dd29'
ESCALATION_STATUS: '8d784bd0-18e5-4db3-b45e-9a2900262e04'
ESCALATED_TO: '934811f1-239f-4d53-880c-3655571fd02e'
ESCALATION_TIMESTAMP: '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f'
SUPERVISOR_RESPONSE: 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86'
ESCALATION_RESOLVED_TIMESTAMP: 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
```

### New Fields (7) - FILL IN AFTER CREATION
```javascript
PROPERTY_LINK: '________________' // TODO
AI_GRADE_OF_RESPONSE: '________________' // TODO
ESCALATION_LEVEL: '________________' // TODO
RFI_STATUS: '________________' // TODO
RFI_REQUEST: '________________' // TODO
RFI_RESPONSE: '________________' // TODO
ESCALATION_HISTORY: '________________' // TODO
```

---

## ⚠️ CRITICAL NOTES

1. **ESCALATION_STATUS must be updated FIRST** before any code changes in Phase 2+
2. **PROPERTY_LINK is CRITICAL** - entire n8n integration depends on this field existing
3. **Do NOT proceed to Phase 2** until all UUIDs are filled in and verified
4. **Backup strategy:** Keep existing escalation flow working while building new features

---

## 🎯 Success Criteria

Phase 1 is complete when:
- [ ] All 16 escalation fields exist in ClickUp
- [ ] All UUIDs are updated in both frontend and backend code
- [ ] All fields can be read via ClickUp API
- [ ] All fields can be written via ClickUp API
- [ ] No `TODO_GET_FROM_CLICKUP` strings remain in code
- [ ] Verification tests pass

---

## 📞 Next Steps

After Phase 1 completion:
1. ✅ Commit code changes with message: "Phase 1: Add escalation custom field constants"
2. ✅ Move to **PHASE 2: Property Link Validation**
3. ✅ Document actual UUIDs for reference

---

**Last Updated:** 2025-10-08
**Owner:** Christian Johnston
