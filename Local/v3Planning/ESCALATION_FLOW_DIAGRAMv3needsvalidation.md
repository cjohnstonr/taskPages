# Escalation System - Complete Flow Diagram

## **LEGEND**
- 🔵 = Employee Action
- 🟣 = Supervisor Action
- 🟠 = Christian (Level 2) Action
- 🤖 = System/AI Action
- 📝 = Custom Field Update
- 🖥️ = UI Change

---

## **FLOW 1: Simple Escalation (No RFI)**

```
┌─────────────────────────────────────────────────────────────┐
│ INITIAL STATE                                               │
├─────────────────────────────────────────────────────────────┤
│ 📝 ESCALATION_STATUS = 0 (Not Escalated)                    │
│ 📝 RFI_STATUS = 0 (None)                                    │
│ 🖥️ UI: Employee sees task details                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
                 🔵 Employee clicks "Escalate Task"
                          ↓
              🤖 System validates property link exists
                          ↓
         ┌────────────────┴────────────────┐
         │                                 │
    NO PROPERTY LINK               PROPERTY LINK EXISTS
         │                                 │
         ↓                                 ↓
    🖥️ BLOCK                      🖥️ Show escalation form
    "Add property link first"              ↓
                                  🔵 Employee enters reason
                                           ↓
                              🔵 Employee clicks "Submit"
                                           ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING                                           │
├─────────────────────────────────────────────────────────────┤
│ 📝 ESCALATION_REASON = "User's text"                        │
│ 📝 ESCALATION_TIMESTAMP = Current time                      │
│ 📝 ESCALATION_STATUS = 1 (Escalated Level 1)                │
│ 📝 ESCALATION_LEVEL = 1 (Supervisor)                        │
│ 📝 RFI_STATUS = 0 (None)                                    │
│                                                             │
│ 🤖 Send to n8n webhook:                                     │
│    {task_id, property_link}                                 │
│                                                             │
│ 🤖 n8n analyzes context + SOPs                              │
│                                                             │
│ 📝 ESCALATION_AI_SUGGESTION = "AI's suggested solution"     │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EMPLOYEE VIEW - ESCALATED STATE                             │
├─────────────────────────────────────────────────────────────┤
│ 🖥️ Shows:                                                   │
│    ✅ "Escalation submitted"                                │
│    📄 AI Suggested Solution: [ESCALATION_AI_SUGGESTION]     │
│    ⏳ "Waiting for supervisor response..."                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR VIEW - REVIEW STATE                              │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 1 AND RFI_STATUS = 0            │
│                                                             │
│ 🖥️ Shows:                                                   │
│    📄 Escalation Reason: [ESCALATION_REASON]                │
│    🤖 AI Suggestion: [ESCALATION_AI_SUGGESTION]             │
│    📄 Full task context                                     │
│                                                             │
│    🎛️ 3 Action Buttons:                                    │
│    ┌──────────┐ ┌─────────────┐ ┌────────────────┐         │
│    │ ✅ Answer│ │ ❓ Request   │ │ ⬆️ Escalate to │         │
│    │          │ │    Info     │ │    Level 2     │         │
│    └──────────┘ └─────────────┘ └────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  🟣 Supervisor clicks "Answer"
                          ↓
              🟣 Supervisor enters response text
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING - RESOLUTION                              │
├─────────────────────────────────────────────────────────────┤
│ 📝 SUPERVISOR_RESPONSE = "Supervisor's answer"              │
│ 📝 ESCALATION_STATUS = 2 (Resolved)                         │
│ 📝 ESCALATION_RESOLVED_TIMESTAMP = Current time             │
│                                                             │
│ 🤖 Send to n8n for grading:                                 │
│    {supervisor_answer, ai_suggestion}                       │
│                                                             │
│ 📝 AI_GRADE_OF_RESPONSE = "AI's evaluation"                 │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ BOTH USERS VIEW - RESOLVED STATE                            │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 2                               │
│                                                             │
│ 🖥️ Shows:                                                   │
│    ✅ "Escalation Resolved"                                 │
│    📄 Original Reason: [ESCALATION_REASON]                  │
│    🤖 AI Suggestion: [ESCALATION_AI_SUGGESTION]             │
│    👤 Supervisor Response: [SUPERVISOR_RESPONSE]            │
│    📊 AI Grade: [AI_GRADE_OF_RESPONSE]                      │
│    📅 Resolved: [ESCALATION_RESOLVED_TIMESTAMP]             │
└─────────────────────────────────────────────────────────────┘
```

---

## **FLOW 2: With RFI (Request for Information)**

```
┌─────────────────────────────────────────────────────────────┐
│ STARTING STATE (Already Escalated)                          │
├─────────────────────────────────────────────────────────────┤
│ 📝 ESCALATION_STATUS = 1 (Escalated Level 1)                │
│ 📝 RFI_STATUS = 0 (None)                                    │
│ 📝 ESCALATION_REASON = "Need help with property issue"      │
│ 📝 ESCALATION_AI_SUGGESTION = "Check property records"      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR VIEW                                             │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 1 AND RFI_STATUS = 0            │
│                                                             │
│ 🟣 Supervisor reviews and thinks:                           │
│    "I need the property address to help"                    │
│                                                             │
│ 🟣 Clicks "Request Info" button                             │
│                                                             │
│ 🟣 Enters in text box:                                      │
│    "What is the exact property address?"                    │
│                                                             │
│ 🟣 Clicks "Submit Request"                                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING - RFI REQUEST                             │
├─────────────────────────────────────────────────────────────┤
│ 📝 RFI_STATUS = 1 (RFI Requested)                           │
│ 📝 RFI_REQUEST = "What is the exact property address?"      │
│ 📝 ESCALATION_STATUS = 1 (STAYS Level 1 - doesn't change!)  │
│                                                             │
│ 💬 Add comment to ClickUp task with RFI request             │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EMPLOYEE VIEW - RFI PENDING STATE                           │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 1 AND RFI_STATUS = 1            │
│                                                             │
│ 🖥️ Shows:                                                   │
│    🟡 "Supervisor Needs More Information"                   │
│    📄 Supervisor's Question: [RFI_REQUEST]                  │
│    "What is the exact property address?"                    │
│                                                             │
│    📝 Text box to respond                                   │
│    ┌─────────────────────────────────┐                      │
│    │ [Employee types response here]  │                      │
│    └─────────────────────────────────┘                      │
│    ┌──────────────────┐                                     │
│    │ Submit Response  │                                     │
│    └──────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR VIEW - WHILE WAITING                             │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 1 AND RFI_STATUS = 1            │
│                                                             │
│ 🖥️ Shows:                                                   │
│    ⏳ "Waiting for employee response..."                    │
│    📄 Your Request: [RFI_REQUEST]                           │
│    "What is the exact property address?"                    │
│                                                             │
│    (No action buttons - just waiting)                       │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  🔵 Employee enters response:
                  "123 Main Street, Unit 5B"
                          ↓
                  🔵 Employee clicks "Submit Response"
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING - RFI RESPONSE                            │
├─────────────────────────────────────────────────────────────┤
│ 📝 RFI_STATUS = 2 (RFI Completed)                           │
│ 📝 RFI_RESPONSE = "123 Main Street, Unit 5B"                │
│ 📝 ESCALATION_STATUS = 1 (STILL Level 1 - back to supervisor)│
│                                                             │
│ 💬 Add comment to ClickUp task with RFI response            │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR VIEW - RFI COMPLETED STATE                       │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 1 AND RFI_STATUS = 2            │
│                                                             │
│ 🖥️ Shows:                                                   │
│    ✅ "Employee Responded!"                                 │
│    📄 Your Question: [RFI_REQUEST]                          │
│    📄 Employee's Answer: [RFI_RESPONSE]                     │
│    "123 Main Street, Unit 5B"                               │
│                                                             │
│    🎛️ 3 Action Buttons (same as before):                   │
│    ┌──────────┐ ┌─────────────┐ ┌────────────────┐         │
│    │ ✅ Answer│ │ ❓ Request   │ │ ⬆️ Escalate to │         │
│    │          │ │  More Info  │ │    Level 2     │         │
│    └──────────┘ └─────────────┘ └────────────────┘         │
│                                                             │
│ Note: If clicks "Request More Info" again:                  │
│       → RFI_STATUS goes back to 1                           │
│       → New RFI_REQUEST overwrites old one                  │
│       → Previous RFI_RESPONSE preserved                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
            🟣 Supervisor now has info, clicks "Answer"
                          ↓
                    (Goes to RESOLVED state)
```

---

## **FLOW 3: Escalate to Level 2 (Christian)**

```
┌─────────────────────────────────────────────────────────────┐
│ STARTING STATE (Supervisor can't resolve)                   │
├─────────────────────────────────────────────────────────────┤
│ 📝 ESCALATION_STATUS = 1 (Escalated Level 1)                │
│ 📝 ESCALATION_LEVEL = 1 (Supervisor)                        │
│ 📝 RFI_STATUS = 0 or 2 (no active RFI)                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SUPERVISOR VIEW                                             │
├─────────────────────────────────────────────────────────────┤
│ 🟣 Supervisor thinks: "This needs Christian's input"        │
│                                                             │
│ 🟣 Clicks "Escalate to Level 2" button                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ ESCALATION FORM (PRE-POPULATED)                             │
├─────────────────────────────────────────────────────────────┤
│ 🖥️ Shows:                                                   │
│    📄 Original Reason (read-only):                          │
│    [ESCALATION_REASON]                                      │
│                                                             │
│    📄 AI Suggestion (read-only):                            │
│    [ESCALATION_AI_SUGGESTION]                               │
│                                                             │
│    📝 Additional Context (editable):                        │
│    ┌─────────────────────────────────────────┐              │
│    │ Supervisor can add more details here    │              │
│    │ about why Level 2 is needed             │              │
│    └─────────────────────────────────────────┘              │
│                                                             │
│    🟣 Clicks "Escalate to Christian"                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING - LEVEL 2 ESCALATION                      │
├─────────────────────────────────────────────────────────────┤
│ 📝 ESCALATION_STATUS = 4 (Escalated Level 2)                │
│ 📝 ESCALATION_LEVEL = 2 (Christian)                         │
│ 📝 ESCALATION_REASON = Original + Additional context        │
│ 📝 RFI_STATUS = 0 (Reset - new level, fresh start)          │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ EMPLOYEE VIEW - LEVEL 2 STATE                               │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 4                               │
│                                                             │
│ 🖥️ Shows:                                                   │
│    🔴 "Escalated to Level 2 (Christian)"                    │
│    ⏳ "Awaiting response from senior management..."         │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ CHRISTIAN VIEW - LEVEL 2 REVIEW                             │
├─────────────────────────────────────────────────────────────┤
│ Checks: ESCALATION_STATUS = 4                               │
│                                                             │
│ 🖥️ Shows:                                                   │
│    🔴 "Level 2 Escalation"                                  │
│    📄 Original Reason: [ESCALATION_REASON]                  │
│    📄 Supervisor's Context: [additional text]               │
│    🤖 AI Suggestion: [ESCALATION_AI_SUGGESTION]             │
│    📄 Full task tree context                                │
│                                                             │
│    🎛️ Christian's Action Buttons:                          │
│    ┌──────────┐ ┌─────────────┐                             │
│    │ ✅ Answer│ │ ❓ Request   │                             │
│    │          │ │    Info     │                             │
│    └──────────┘ └─────────────┘                             │
│                                                             │
│ Note: RFI works same as Level 1                             │
│       → Can request info from employee                      │
│       → RFI_STATUS = 1 → 2 cycle                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
                  🟠 Christian clicks "Answer"
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM PROCESSING - LEVEL 2 RESOLUTION                      │
├─────────────────────────────────────────────────────────────┤
│ 📝 SUPERVISOR_RESPONSE = "Christian's answer"               │
│ 📝 ESCALATION_STATUS = 2 (Resolved)                         │
│ 📝 ESCALATION_RESOLVED_TIMESTAMP = Current time             │
│                                                             │
│ 🤖 Send to n8n for grading (optional at L2)                 │
│                                                             │
│ 📝 AI_GRADE_OF_RESPONSE = "AI's evaluation"                 │
│                                                             │
│ 🖥️ Page reloads                                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
                     (RESOLVED STATE)
```

---

## **COMPLETE CUSTOM FIELD STATE TABLE**

| Field Name | Initial Value | Set When | Set To | Reset When |
|------------|--------------|----------|--------|------------|
| **ESCALATION_STATUS** | 0 | Employee escalates | 1 | Never (flows forward only) |
| | | Escalate to L2 | 4 | |
| | | Resolved | 2 | |
| **ESCALATION_LEVEL** | - | Employee escalates | 1 (Supervisor) | Never |
| | | Escalate to L2 | 2 (Christian) | |
| **ESCALATION_REASON** | - | Employee escalates | User's text | Appended on L2 escalation |
| **ESCALATION_TIMESTAMP** | - | Employee escalates | Current time | Never |
| **ESCALATION_AI_SUGGESTION** | - | After n8n response | AI's text | Never |
| **RFI_STATUS** | 0 (None) | Supervisor requests info | 1 (Requested) | Back to 0 on L2 escalation |
| | | Employee responds | 2 (Completed) | |
| | | Request more info | 1 (Requested) | |
| **RFI_REQUEST** | - | Supervisor requests info | Supervisor's question | Overwritten on new request |
| **RFI_RESPONSE** | - | Employee responds | Employee's answer | Preserved (not cleared) |
| **SUPERVISOR_RESPONSE** | - | Answer submitted | Response text | Never |
| **ESCALATION_RESOLVED_TIMESTAMP** | - | Resolved | Current time | Never |
| **AI_GRADE_OF_RESPONSE** | - | After n8n grading | Grade text | Never |
| **ESCALATION_HISTORY** | [] | Each state change | Append JSON log | Never (only appends) |
| **PROPERTY_LINK** | - | Pre-escalation | Task ID (if copied from parent) | Never |

---

## **UI STATE DETECTION LOGIC**

```javascript
function determineUIState(task) {
    const escalationStatus = getCustomField(task, FIELD_IDS.ESCALATION_STATUS);
    const rfiStatus = getCustomField(task, FIELD_IDS.RFI_STATUS);
    const escalationLevel = getCustomField(task, FIELD_IDS.ESCALATION_LEVEL);

    // NOT ESCALATED
    if (escalationStatus === 0) {
        return {
            state: 'NOT_ESCALATED',
            employeeView: 'EscalationForm',
            supervisorView: 'NoAccess'
        };
    }

    // ESCALATED LEVEL 1
    if (escalationStatus === 1) {
        if (rfiStatus === 1) {
            return {
                state: 'RFI_PENDING',
                employeeView: 'RFIResponseForm',
                supervisorView: 'WaitingForEmployee'
            };
        }
        if (rfiStatus === 2) {
            return {
                state: 'RFI_COMPLETED',
                employeeView: 'WaitingForSupervisor',
                supervisorView: 'ActionPanelWithRFIResponse'
            };
        }
        return {
            state: 'ESCALATED_L1',
            employeeView: 'WaitingForSupervisor',
            supervisorView: 'ActionPanel'
        };
    }

    // ESCALATED LEVEL 2
    if (escalationStatus === 4) {
        if (rfiStatus === 1) {
            return {
                state: 'L2_RFI_PENDING',
                employeeView: 'RFIResponseForm',
                christianView: 'WaitingForEmployee'
            };
        }
        if (rfiStatus === 2) {
            return {
                state: 'L2_RFI_COMPLETED',
                employeeView: 'WaitingForChristian',
                christianView: 'ActionPanelWithRFIResponse'
            };
        }
        return {
            state: 'ESCALATED_L2',
            employeeView: 'WaitingForChristian',
            christianView: 'ActionPanel'
        };
    }

    // RESOLVED
    if (escalationStatus === 2) {
        return {
            state: 'RESOLVED',
            allUsersView: 'ResolvedDisplay'
        };
    }
}
```

---

**Is this diagram clear? Would you like me to expand any specific flow?**
