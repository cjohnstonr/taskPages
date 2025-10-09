# Escalation System Fields - ACTUAL ClickUp Configuration

**Last Updated:** 2025-10-08
**Source:** ClickUp custom fields export from CLAUDE.md

---

## ✅ ALL FIELDS EXIST IN CLICKUP

All 13 escalation fields have been created and configured. Only missing: **PROPERTY_LINK** field.

---

## 📊 Complete Field Reference

| Field ID | Field Name | Type | Dropdown Options | Purpose |
|----------|------------|------|------------------|---------|
| `c6e0281e-9001-42d7-a265-8f5da6b71132` | **Escalation_Reason_Text** | text | N/A | Employee's explanation of why task needs escalation |
| `e9e831f2-b439-4067-8e88-6b715f4263b2` | **Escalation_Reason_AI** | text | N/A | AI-generated summary of escalation context |
| `bc5e9359-01cd-408f-adb9-c7bdf1f2dd29` | **Escalation_AI_Suggestion** | text | N/A | AI's suggested solution (displayed to employee) |
| `8d784bd0-18e5-4db3-b45e-9a2900262e04` | **Escalation_Status** | drop_down | 0=Not Escalated<br>1=Escalated<br>2=Resolved | Main escalation state |
| `5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f` | **Escalation_Submitted_Date_Time** | date | N/A | When escalation was submitted |
| `a077ecc9-1a59-48af-b2cd-42a63f5a7f86` | **Escalation_Response_Text** | text | N/A | Supervisor's or Christian's response |
| `c40bf1c4-7d33-4b2b-8765-0784cd88591a` | **Escalation_Resolved_Date_Time** | date | N/A | When escalation was resolved |
| `629ca244-a6d3-46dd-9f1e-6a0ded40f519` | **Escalation_AI_Grade** | text | N/A | AI's evaluation of supervisor response |
| `94790367-5d1f-4300-8f79-e13819f910d4` | **Escalation_History** | text | N/A | JSON log of state transitions |
| `90d2fec8-7474-4221-84c0-b8c7fb5e4385` | **Esclation_Level** (typo!) | drop_down | 0=Shirley<br>1=Christian | Escalation level routing |
| `f94c0b4b-0c70-4c23-9633-07af2fa6ddc6` | **Escalation_RFI_Status** | drop_down | 0=RFI Requested<br>1=RFI Completed | RFI conversation tracker |
| `0e7dd6f8-3167-4df5-964e-574734ffd4ed` | **Escalation_RFI_Request** | text | N/A | What information supervisor is requesting |
| `b5c52661-8142-45e0-bec5-14f3c135edbc` | **Escalation_RFI_Response** | text | N/A | Employee's response to RFI |

---

## 🎯 Dropdown Field Details

### **Escalation_Status** (`8d784bd0-18e5-4db3-b45e-9a2900262e04`)

| Order | Label | UUID | Color | Meaning |
|-------|-------|------|-------|---------|
| 0 | Not Escalated | `bf10e6ce-bef9-4105-aa2c-913049e2d4ed` | #FF4081 (Pink) | Initial state |
| 1 | Escalated | `8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497` | #7C4DFF (Purple) | Awaiting supervisor/Christian response |
| 2 | Resolved | `cbf82936-5488-4612-93a7-f8161071b0eb` | #f9d900 (Yellow) | Escalation closed |

**Notes:**
- Currently only 3 states (no separate "Awaiting Info" or "Escalated Level 2")
- RFI tracking handled by separate `Escalation_RFI_Status` field
- Level routing handled by separate `Esclation_Level` field

---

### **Esclation_Level** (`90d2fec8-7474-4221-84c0-b8c7fb5e4385`)

⚠️ **Field Name Has Typo:** "Esclation" instead of "Escalation"

| Order | Label | UUID | Color | Meaning |
|-------|-------|------|-------|---------|
| 0 | Shirley | `cfd3a04c-5b0c-4ddd-b65e-df65bd662ef5` | #FF4081 (Pink) | Level 1 - Supervisor |
| 1 | Christian | `841566bc-4076-433e-af7b-9b5214bdc991` | #7C4DFF (Purple) | Level 2 - Final escalation |

**Usage:**
- Set to `0` (Shirley) when employee submits escalation
- Set to `1` (Christian) when supervisor escalates to level 2

---

### **Escalation_RFI_Status** (`f94c0b4b-0c70-4c23-9633-07af2fa6ddc6`)

| Order | Label | UUID | Color | Meaning |
|-------|-------|------|-------|---------|
| 0 | RFI Requested | `9b404ea6-efb7-40d1-9820-75ed5f5f47ff` | #FF4081 (Pink) | Supervisor asked for info, awaiting employee |
| 1 | RFI Completed | `3e28b07a-361a-4fc8-bc78-0d8774167939` | #7C4DFF (Purple) | Employee responded to RFI |

**⚠️ IMPORTANT:** This dropdown is **missing option for "None"** (no RFI active)

**Workaround Options:**
1. **Option A:** Add "None" option (orderindex 2) to ClickUp dropdown
2. **Option B:** Use `null` or empty value to represent "no RFI" state
3. **Option C:** Check if field is set at all (undefined = no RFI)

**Recommended:** Option B - treat `null` as "no RFI active"

---

## 🔄 State Machine Logic

### **Primary State: Escalation_Status**

```javascript
const escalationStatus = getDropdownValue(field); // Maps orderindex to label
// 0 = "Not Escalated"
// 1 = "Escalated"
// 2 = "Resolved"
```

### **Secondary State: Escalation_Level**

```javascript
const escalationLevel = getDropdownValue(field);
// 0 = "Shirley" (Level 1)
// 1 = "Christian" (Level 2)
```

### **Tertiary State: Escalation_RFI_Status**

```javascript
const rfiStatus = getDropdownValue(field);
// null/undefined = No RFI active
// 0 = "RFI Requested" (awaiting employee)
// 1 = "RFI Completed" (employee responded)
```

### **Combined State Detection**

```javascript
function determineEscalationState(task) {
    const status = getCustomField(task, FIELD_IDS.ESCALATION_STATUS);
    const level = getCustomField(task, FIELD_IDS.ESCALATION_LEVEL);
    const rfiStatus = getCustomField(task, FIELD_IDS.ESCALATION_RFI_STATUS);

    if (status === 0) {
        return 'NOT_ESCALATED';
    }
    else if (status === 1) {
        // ESCALATED state - check level and RFI sub-states

        if (rfiStatus === 0) {
            // RFI Requested - employee needs to respond
            return level === 0 ? 'ESCALATED_L1_RFI_REQUESTED' : 'ESCALATED_L2_RFI_REQUESTED';
        }
        else if (rfiStatus === 1) {
            // RFI Completed - supervisor needs to review response
            return level === 0 ? 'ESCALATED_L1_RFI_COMPLETED' : 'ESCALATED_L2_RFI_COMPLETED';
        }
        else {
            // No RFI active - normal escalated state
            return level === 0 ? 'ESCALATED_LEVEL_1' : 'ESCALATED_LEVEL_2';
        }
    }
    else if (status === 2) {
        return 'RESOLVED';
    }
}
```

---

## 📝 Field Update Patterns

### **Employee Submits Escalation**
```javascript
{
    ESCALATION_REASON_TEXT: "Employee's explanation",
    ESCALATION_REASON_AI: "AI summary",
    ESCALATION_AI_SUGGESTION: "AI suggested solution", // From n8n
    ESCALATION_STATUS: 1, // Escalated
    ESCALATION_LEVEL: 0, // Shirley (Level 1)
    ESCALATION_SUBMITTED_DATE_TIME: timestamp,
    ESCALATION_RFI_STATUS: null // No RFI yet
}
```

### **Supervisor Requests Info (RFI)**
```javascript
{
    ESCALATION_RFI_STATUS: 0, // RFI Requested
    ESCALATION_RFI_REQUEST: "What is the property address?"
    // ESCALATION_STATUS stays 1 (Escalated)
    // ESCALATION_LEVEL stays 0 (Shirley)
}
```

### **Employee Responds to RFI**
```javascript
{
    ESCALATION_RFI_STATUS: 1, // RFI Completed
    ESCALATION_RFI_RESPONSE: "123 Main St, Unit 5B"
    // ESCALATION_STATUS stays 1 (Escalated)
    // Routes back to supervisor
}
```

### **Supervisor Answers (Resolves)**
```javascript
{
    ESCALATION_RESPONSE_TEXT: "Supervisor's answer",
    ESCALATION_STATUS: 2, // Resolved
    ESCALATION_RESOLVED_DATE_TIME: timestamp,
    ESCALATION_AI_GRADE: "AI evaluation" // From n8n
}
```

### **Supervisor Escalates to Level 2**
```javascript
{
    ESCALATION_LEVEL: 1, // Christian (Level 2)
    ESCALATION_RFI_STATUS: null // Reset RFI (new level, fresh start)
    // ESCALATION_STATUS stays 1 (Escalated)
    // Can add to ESCALATION_REASON_AI with additional context
}
```

---

## ⚠️ Critical Issues to Address

### **Issue 1: RFI_STATUS Missing "None" Option**

**Current:** Dropdown only has "RFI Requested" (0) and "RFI Completed" (1)

**Problem:** No way to represent "no RFI active" state

**Solutions:**
1. ✅ **Recommended:** Treat `null`/undefined as "no RFI"
2. Add "None" option to dropdown (orderindex 2)
3. Use field absence to detect no RFI

**Implementation:**
```javascript
function getRFIStatus(task) {
    const field = task.custom_fields.find(f => f.id === FIELD_IDS.ESCALATION_RFI_STATUS);
    if (!field || field.value === null || field.value === undefined) {
        return 'NONE'; // No RFI active
    }
    if (field.value === 0) return 'RFI_REQUESTED';
    if (field.value === 1) return 'RFI_COMPLETED';
}
```

---

### **Issue 2: Field Name Typo**

**Field:** `Esclation_Level` (missing 'a')

**Impact:** Minor - only affects readability in ClickUp UI

**Action:** Can rename in ClickUp if desired, UUID stays same

---

### **Issue 3: Missing PROPERTY_LINK Field**

**Status:** Not yet created in ClickUp

**Required For:** Phase 2 - Property link validation

**Action Needed:** Search ClickUp for existing "Property" relationship field or create new one

---

## 🚀 Next Steps

### **Immediate Actions:**

1. ✅ **DONE:** Update code constants with actual field IDs
2. 🔲 **TODO:** Decide on RFI_STATUS "None" handling (use null vs add option)
3. 🔲 **TODO:** Find or create PROPERTY_LINK field
4. 🔲 **TODO:** Update helper functions to use correct field names
5. 🔲 **TODO:** Test reading all dropdown values with new UUIDs

### **Phase 1 Completion:**

- [x] All field IDs mapped
- [ ] PROPERTY_LINK field identified/created
- [ ] RFI_STATUS "None" state handling decided
- [ ] Code updated to use actual field names
- [ ] Verification testing passed

---

**Last Verified:** 2025-10-08
**Total Fields:** 13 existing + 1 missing (PROPERTY_LINK)
