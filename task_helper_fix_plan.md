# Task Helper Fix Plan

## 1. CUSTOM FIELDS MAPPING

### Fields You Provided:
1. **ESCALATION_REASON** - `c6e0281e-9001-42d7-a265-8f5da6b71132`
   - **When Set**: When user submits escalation
   - **Value**: User's typed reason text

2. **ESCALATION_AI_SUMMARY** - `e9e831f2-b439-4067-8e88-6b715f4263b2`
   - **When Set**: After AI generates summary
   - **Value**: AI-generated context summary

3. **ESCALATION_STATUS** - `8d784bd0-18e5-4db3-b45e-9a2900262e04` (DROPDOWN)
   - **When Set**: Multiple times during workflow
   - **Values**: Need to check ClickUp API for option indexes
     - Not Escalated (default) - index 0?
     - Escalated - index 1? 
     - Resolved - index 2?
   - **CRITICAL**: Must fetch actual dropdown options via API

4. **ESCALATED_TO** - `934811f1-239f-4d53-880c-3655571fd02e`
   - **When Set**: When escalation submitted
   - **Value**: Supervisor/manager user ID or selection

5. **ESCALATION_TIMESTAMP** - `5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f`
   - **When Set**: When escalation submitted
   - **Value**: Unix timestamp in milliseconds

6. **SUPERVISOR_RESPONSE** - `a077ecc9-1a59-48af-b2cd-42a63f5a7f86`
   - **When Set**: When supervisor responds
   - **Value**: Supervisor's resolution text

7. **ESCALATION_RESOLVED_TIMESTAMP** - `c40bf1c4-7d33-4b2b-8765-0784cd88591a`
   - **When Set**: When supervisor marks as resolved
   - **Value**: Unix timestamp in milliseconds

## 2. WORKFLOW STAGES & UI CHANGES

### Stage 1: Not Escalated (Default)
- **Fields Present**: None or ESCALATION_STATUS = 0
- **UI Shows**: 
  - Parent task info (if exists)
  - Current task info
  - Escalation form

### Stage 2: User Submits Escalation
- **Fields Set**:
  - ESCALATION_REASON = user text
  - ESCALATION_STATUS = 1 (Escalated)
  - ESCALATION_TIMESTAMP = now
  - ESCALATED_TO = selected supervisor
- **UI Action**: Generate AI summary

### Stage 3: AI Summary Generated
- **Fields Set**:
  - ESCALATION_AI_SUMMARY = AI text
- **UI Shows**: 
  - Escalation submitted confirmation
  - Page refreshes to show escalated state

### Stage 4: Escalated (Awaiting Response)
- **Fields Present**: All escalation fields filled, no supervisor response
- **UI Shows**:
  - Read-only escalation details
  - Supervisor response form (if viewer is supervisor)
  - Status: "Awaiting supervisor response"

### Stage 5: Supervisor Responds
- **Fields Set**:
  - SUPERVISOR_RESPONSE = supervisor text
  - ESCALATION_STATUS = 2 (Resolved)
  - ESCALATION_RESOLVED_TIMESTAMP = now
- **UI Shows**:
  - Complete escalation history
  - Resolution details

## 3. NEW LAYOUT DESIGN

```
┌─────────────────────────────────────────┐
│          Task Helper                    │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   PARENT TASK INFO (if exists)  │   │
│  │   - Name                        │   │
│  │   - Description                 │   │
│  │   - Custom Fields (non-empty)   │   │
│  │   - Comments (collapsible)      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   CURRENT TASK INFO             │   │
│  │   - Name                        │   │
│  │   - Description                 │   │
│  │   - Custom Fields (non-empty)   │   │
│  │   - Comments (collapsible)      │   │
│  └─────────────────────────────────┘   │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │   ESCALATION MODULE             │   │
│  │   Dynamic based on status:      │   │
│  │   - Form (if not escalated)     │   │
│  │   - Status (if escalated)       │   │
│  │   - Response (if supervisor)    │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

## 4. IMPLEMENTATION STEPS

1. **Fix Custom Field Updates**
   - Update backend to use all 7 fields
   - Fetch dropdown options for ESCALATION_STATUS
   - Handle dropdown value correctly (use orderindex)

2. **Replace Accordion with Sidebar Layout**
   - Port TaskDetailsSection from wait-node
   - Show parent task info cleanly
   - Show current task info with non-empty fields

3. **Add Field Presence Detection**
   - Check which custom fields are filled
   - Change UI based on escalation state
   - Show supervisor response form conditionally

4. **Implement Supervisor Workflow**
   - Detect if current user is supervisor
   - Show response form if escalated & is supervisor
   - Update fields on supervisor submit

5. **Add Page Refresh**
   - After escalation submitted
   - After supervisor responds
   - To show updated state

## 5. CRITICAL FIXES NEEDED

1. **Dropdown Field Handling**
   ```python
   # Need to fetch options first:
   response = requests.get(
       f"https://api.clickup.com/api/v2/list/{list_id}/field/{field_id}",
       headers={"Authorization": clickup_token}
   )
   options = response.json()['type_config']['options']
   # Find correct index for "Escalated"
   escalated_index = next(i for i, opt in enumerate(options) if opt['name'] == 'Escalated')
   ```

2. **Show Only Non-Empty Custom Fields**
   ```javascript
   const nonEmptyFields = Object.entries(FIELD_IDS)
     .map(([name, id]) => ({name, value: getCustomField(task, id)}))
     .filter(field => field.value && field.value !== '')
   ```

3. **Conditional UI Based on Status**
   ```javascript
   const escalationStatus = getCustomField(task, FIELD_IDS.ESCALATION_STATUS);
   const supervisorResponse = getCustomField(task, FIELD_IDS.SUPERVISOR_RESPONSE);
   
   if (!escalationStatus || escalationStatus === 0) {
     // Show escalation form
   } else if (escalationStatus === 1 && !supervisorResponse) {
     // Show awaiting response + supervisor form if applicable
   } else if (supervisorResponse) {
     // Show complete resolution
   }
   ```