 CURRENT STATE MANAGEMENT AUDIT

  Table 1: Frontend State Detection Logic

  | Location               | State Detection Code                                                      | Fields Checked                                              | State Determined
             |
  |------------------------|---------------------------------------------------------------------------|-------------------------------------------------------------|-------------------------------------
  -----------|
  | escalation-v2.html:485 | const escalationStatus = getEscalationStatus(task)                        | ESCALATION_STATUS dropdown                                  | NOT_ESCALATED (0), ESCALATED (1),
  RESOLVED (2) |
  | escalation-v2.html:486 | const isEscalated = escalationStatus === 'ESCALATED' || reason || summary | ESCALATION_STATUS, ESCALATION_REASON, ESCALATION_AI_SUMMARY | Boolean: Is task escalated?
             |
  | escalation-v2.html:487 | const isResolved = escalationStatus === 'RESOLVED' || supervisorResponse  | ESCALATION_STATUS, SUPERVISOR_RESPONSE                      | Boolean: Is escalation resolved?
             |
  | escalation-v2.html:488 | const isAwaitingResponse = isEscalated && !isResolved                     | Combined logic                                              | Boolean: Waiting for supervisor?
             |

  Table 2: Current UI State Rendering

  | State Detected                | UI Component Rendered   | Location      | Actions Available                                                        | Background Color       |
  |-------------------------------|-------------------------|---------------|--------------------------------------------------------------------------|------------------------|
  | NOT_ESCALATED                 | Escalation Form         | Lines 704-758 | 1. Enter escalation reason2. Generate AI Summary3. Submit Escalation     | White with gray border |
  | ESCALATED (Awaiting Response) | Pending Status Display  | Lines 652-700 | 1. View escalation details2. Enter supervisor response3. Submit Response | Yellow (bg-yellow-50)  |
  | RESOLVED                      | Resolution Confirmation | Lines 619-648 | Read-only display                                                        | Green (bg-green-50)    |

  Table 3: Current Backend API Endpoints

  | Endpoint                                       | Method | Location              | Purpose                           | Fields Updated
                        | State Transition          |
  |------------------------------------------------|--------|-----------------------|-----------------------------------|----------------------------------------------------------------------------------
  ----------------------|---------------------------|
  | /api/task-helper/escalate/<task_id>            | POST   | app_secure.py:702-851 | Submit initial escalation         | ESCALATION_REASONESCALATION_AI_SUMMARYESCALATION_STATUS →
  1ESCALATION_TIMESTAMPESCALATED_TO (optional) | NOT_ESCALATED → ESCALATED |
  | /api/task-helper/supervisor-response/<task_id> | POST   | app_secure.py:854-952 | Submit supervisor resolution      | SUPERVISOR_RESPONSEESCALATION_STATUS → 2ESCALATION_RESOLVED_TIMESTAMP
                        | ESCALATED → RESOLVED      |
  | /api/ai/generate-escalation-summary            | POST   | Referenced line 513   | Generate AI summary of escalation | None (returns text only)
                        | No state change           |

  Table 4: Current Field Update Patterns

  | Field ID                             | Field Name                    | When Set                      | Set By      | Value Type           | Location               |
  |--------------------------------------|-------------------------------|-------------------------------|-------------|----------------------|------------------------|
  | c6e0281e-9001-42d7-a265-8f5da6b71132 | ESCALATION_REASON             | Initial escalation            | Employee    | Text (user input)    | Backend line 753       |
  | e9e831f2-b439-4067-8e88-6b715f4263b2 | ESCALATION_AI_SUMMARY         | Initial escalation            | System (AI) | Text (AI generated)  | Backend line 754       |
  | 8d784bd0-18e5-4db3-b45e-9a2900262e04 | ESCALATION_STATUS             | Escalation & Resolution       | System      | Dropdown: 0/1/2      | Backend lines 755, 897 |
  | 934811f1-239f-4d53-880c-3655571fd02e | ESCALATED_TO                  | Initial escalation (optional) | Employee    | Text (user ID/email) | Backend line 764       |
  | 5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f | ESCALATION_TIMESTAMP          | Initial escalation            | System      | Date (Unix ms)       | Backend lines 756-759  |
  | a077ecc9-1a59-48af-b2cd-42a63f5a7f86 | SUPERVISOR_RESPONSE           | Resolution                    | Supervisor  | Text (response)      | Backend line 896       |
  | c40bf1c4-7d33-4b2b-8765-0784cd88591a | ESCALATION_RESOLVED_TIMESTAMP | Resolution                    | System      | Date (Unix ms)       | Backend lines 898-901  |

  Table 5: Current User Flow

  | Step | User Action                 | Frontend Handler                    | Backend Endpoint                               | Fields Updated        | Next State        |
  |------|-----------------------------|-------------------------------------|------------------------------------------------|-----------------------|-------------------|
  | 1    | Click "Escalate Task"       | Component renders form              | None                                           | None                  | Form displayed    |
  | 2    | Enter escalation reason     | setEscalationText() line 718        | None                                           | Local state only      | -                 |
  | 3    | Click "Generate AI Summary" | generateSummary() line 505          | /api/ai/generate-escalation-summary            | Local state aiSummary | -                 |
  | 4    | Click "Submit Escalation"   | submitEscalation() line 549         | /api/task-helper/escalate/{task_id}            | 5 fields updated      | ESCALATED         |
  | 5    | Page reloads                | window.location.reload() line 574   | None                                           | None                  | Shows pending UI  |
  | 6    | Supervisor enters response  | setSupervisorText() line 687        | None                                           | Local state only      | -                 |
  | 7    | Click "Submit Response"     | submitSupervisorResponse() line 588 | /api/task-helper/supervisor-response/{task_id} | 3 fields updated      | RESOLVED          |
  | 8    | Page reloads                | window.location.reload() line 605   | None                                           | None                  | Shows resolved UI |

  Table 6: Current Data Flow

  | Direction          | From                   | To                                      | Data Passed                                      | Method               |
  |--------------------|------------------------|-----------------------------------------|--------------------------------------------------|----------------------|
  | Frontend → Backend | escalation-v2.html:558 | /api/task-helper/escalate               | {reason, ai_summary, escalated_to, task_context} | POST JSON            |
  | Backend → ClickUp  | app_secure.py:768-772  | ClickUp API /task/{id}/field/{field_id} | Individual field updates                         | POST (one per field) |
  | Backend → Frontend | app_secure.py:843      | escalation-v2.html                      | {success, escalation_id, task_id, ...}           | JSON response        |
  | Frontend → Backend | escalation-v2.html:597 | /api/task-helper/supervisor-response    | {response}                                       | POST JSON            |
  | Backend → ClickUp  | app_secure.py:906-910  | ClickUp API /task/{id}/field/{field_id} | Individual field updates                         | POST (one per field) |

  ---
  Now let me create the DESIRED STATE tables:

⏺ DESIRED STATE MANAGEMENT (NEW SYSTEM)

  Table 7: New State Machine

  | State Name        | Dropdown Value | Description                                      | Who Can Act    | Available Actions                               |
  |-------------------|----------------|--------------------------------------------------|----------------|-------------------------------------------------|
  | NOT_ESCALATED     | 0              | Initial state - no escalation                    | Employee       | Submit Escalation (if property link exists)     |
  | ESCALATED_LEVEL_1 | 1              | Escalated to supervisor, AI suggestion displayed | Supervisor     | Answer, Request Info (RFI), Escalate to Level 2 |
  | AWAITING_INFO     | 3 (NEW)        | Supervisor requested more info from employee     | Employee       | Respond to RFI                                  |
  | ESCALATED_LEVEL_2 | 4 (NEW)        | Escalated to Christian (Level 2)                 | Christian only | Answer, Request Info (RFI)                      |
  | RESOLVED          | 2              | Escalation resolved with answer                  | Read-only      | None                                            |

  Table 8: New Custom Fields Required

  | Field Name           | Field ID     | Type              | Set When                      | Set By                                | Purpose                               |
  |----------------------|--------------|-------------------|-------------------------------|---------------------------------------|---------------------------------------|
  | PROPERTY_LINK        | TBD/existing | Task relationship | Pre-escalation validation     | System (copied from parent if needed) | Links task to property for context    |
  | AI_SUGGESTION        | TBD          | Text              | After n8n webhook response    | n8n automation                        | AI's suggested solution based on SOPs |
  | AI_SOLUTION_DISPLAY  | TBD          | Text              | Same as AI_SUGGESTION         | System (copy of AI_SUGGESTION)        | Shows AI suggestion to employee       |
  | AI_GRADE_OF_RESPONSE | TBD          | Text or Number    | After supervisor responds     | n8n automation                        | AI's evaluation of human response     |
  | ESCALATION_LEVEL     | TBD          | Dropdown          | On escalation submit/escalate | System                                | 1 = Supervisor, 2 = Christian         |
  | RFI_STATUS           | TBD          | Dropdown          | When supervisor clicks RFI    | System                                | Active, Responded, Resolved           |
  | RFI_REQUEST          | TBD          | Text              | When supervisor clicks RFI    | Supervisor                            | What information is being requested   |
  | RFI_RESPONSE         | TBD          | Text              | When employee responds to RFI | Employee                              | Employee's response to info request   |
  | ESCALATION_HISTORY   | TBD          | Text (JSON)       | On each state change          | System                                | Log of all state transitions          |

  Table 9: New Backend Endpoints Needed

  | Endpoint                                          | Method | Purpose                                                                                    | Input                | Fields Updated
                                                                             | State Transition                      |
  |---------------------------------------------------|--------|--------------------------------------------------------------------------------------------|----------------------|-----------------------
  ---------------------------------------------------------------------------|---------------------------------------|
  | /api/task-helper/validate-property-link/<task_id> | GET    | Pre-escalation: Check if property link exists on task or parent                            | task_id              | Sets PROPERTY_LINK on
  subtask if missing                                                         | None (validation only)                |
  | /api/task-helper/escalate-with-ai/<task_id>       | POST   | New escalation flow: Validate property → Send to n8n → Get AI suggestion → Save all fields | {reason, task_id}    | All escalation fields
  + AI_SUGGESTION + ESCALATION_LEVEL=1                                       | NOT_ESCALATED → ESCALATED_LEVEL_1     |
  | /api/task-helper/supervisor-answer/<task_id>      | POST   | Supervisor answers (replaces current supervisor-response)                                  | {answer}             | SUPERVISOR_RESPONSE +
  ESCALATION_STATUS=2 + sends to n8n for grading → sets AI_GRADE_OF_RESPONSE | ESCALATED_LEVEL_1 → RESOLVED          |
  | /api/task-helper/request-info/<task_id>           | POST   | Supervisor requests more info from employee                                                | {info_request}       | RFI_STATUS=Active +
  RFI_REQUEST + ESCALATION_STATUS=3                                            | ESCALATED_LEVEL_1 → AWAITING_INFO     |
  | /api/task-helper/respond-to-rfi/<task_id>         | POST   | Employee responds to RFI                                                                   | {rfi_response}       | RFI_RESPONSE +
  RFI_STATUS=Responded + ESCALATION_STATUS=1                                        | AWAITING_INFO → ESCALATED_LEVEL_1     |
  | /api/task-helper/escalate-to-level-2/<task_id>    | POST   | Supervisor escalates to Christian                                                          | {additional_context} | ESCALATION_LEVEL=2 +
  ESCALATION_STATUS=4 + appends context                                       | ESCALATED_LEVEL_1 → ESCALATED_LEVEL_2 |
  | /api/task-helper/christian-answer/<task_id>       | POST   | Christian (Level 2) answers                                                                | {answer}             | SUPERVISOR_RESPONSE +
  ESCALATION_STATUS=2                                                        | ESCALATED_LEVEL_2 → RESOLVED          |

  Table 10: New User Flow (Employee Escalation)

  | Step | User Action                            | Frontend Handler        | Backend Endpoint                                  | External Call                            | Fields Updated
                                                                                                               | Next State                                |
  |------|----------------------------------------|-------------------------|---------------------------------------------------|------------------------------------------|-------------------------------
  -------------------------------------------------------------------------------------------------------------|-------------------------------------------|
  | 1    | Click "Escalate Task"                  | Pre-flight validation   | /api/task-helper/validate-property-link/{task_id} | None                                     | PROPERTY_LINK (if copied from
  parent)                                                                                                      | Continue or Block                         |
  | 1a   | IF NO PROPERTY LINK                    | Show error message      | None                                              | None                                     | None
                                                                                                               | BLOCKED - Employee must add property link |
  | 2    | Enter escalation reason                | setEscalationText()     | None                                              | None                                     | Local state
                                                                                                               | -                                         |
  | 3    | Click "Generate AI Summary" (optional) | generateSummary()       | /api/ai/generate-escalation-summary               | None                                     | Local state aiSummary
                                                                                                               | -                                         |
  | 4    | Click "Submit Escalation"              | submitEscalation()      | /api/task-helper/escalate-with-ai/{task_id}       | n8n webhook with task_id + property_link |
  ESCALATION_REASONESCALATION_AI_SUMMARYESCALATION_STATUS=1ESCALATION_LEVEL=1ESCALATION_TIMESTAMPAI_SUGGESTION (from n8n)AI_SOLUTION_DISPLAY | ESCALATED_LEVEL_1                         |
  | 5    | View AI suggestion                     | Component auto-displays | None                                              | None                                     | None
                                                                                                               | Shows AI suggestion to employee           |
  | 6    | Wait for supervisor                    | -                       | -                                                 | -                                        | -
                                                                                                               | -                                         |

  Table 11: New User Flow (Supervisor Actions)

  | Step | User Action                   | Frontend Handler         | Backend Endpoint                               | External Call                 | Fields Updated
                                                 | Next State        |
  |------|-------------------------------|--------------------------|------------------------------------------------|-------------------------------|-----------------------------------------------------
  -----------------------------------------------|-------------------|
  | 7a   | Option A: Answer              | submitSupervisorAnswer() | /api/task-helper/supervisor-answer/{task_id}   | n8n webhook to grade response |
  SUPERVISOR_RESPONSEESCALATION_STATUS=2ESCALATION_RESOLVED_TIMESTAMPAI_GRADE_OF_RESPONSE (from n8n) | RESOLVED          |
  | 7b   | Option B: Request Info        | submitRFIRequest()       | /api/task-helper/request-info/{task_id}        | ClickUp comment API           | RFI_REQUESTRFI_STATUS=ActiveESCALATION_STATUS=3
                                                 | AWAITING_INFO     |
  | 7c   | Option C: Escalate to Level 2 | escalateToLevel2()       | /api/task-helper/escalate-to-level-2/{task_id} | None                          | ESCALATION_LEVEL=2ESCALATION_STATUS=4Appends context
   to ESCALATION_REASON                          | ESCALATED_LEVEL_2 |

  Table 12: New User Flow (RFI Response)

  | Step | User Action                       | Frontend Handler          | Backend Endpoint                          | Fields Updated                                      | Next State
           |
  |------|-----------------------------------|---------------------------|-------------------------------------------|-----------------------------------------------------|-------------------------------
  ---------|
  | 8    | Employee sees RFI request         | Component displays RFI UI | None                                      | None                                                | Shows RFI request
           |
  | 9    | Employee enters response          | setRFIResponse()          | None                                      | Local state                                         | -
           |
  | 10   | Employee clicks "Submit Response" | submitRFIResponse()       | /api/task-helper/respond-to-rfi/{task_id} | RFI_RESPONSERFI_STATUS=RespondedESCALATION_STATUS=1 | ESCALATED_LEVEL_1 (back to
  supervisor) |

  Table 13: New User Flow (Christian Level 2)

  | Step | User Action                       | Frontend Handler                            | Backend Endpoint                            | External Call                   | Fields Updated
                                                                       | Next State |
  |------|-----------------------------------|---------------------------------------------|---------------------------------------------|---------------------------------|-------------------------------
  ---------------------------------------------------------------------|------------|
  | 11   | Christian sees Level 2 escalation | Component shows all context + AI suggestion | None                                        | None                            | None
                                                                       | -          |
  | 12   | Christian answers                 | submitChristianAnswer()                     | /api/task-helper/christian-answer/{task_id} | n8n webhook to grade (optional) |
  SUPERVISOR_RESPONSEESCALATION_STATUS=2ESCALATION_RESOLVED_TIMESTAMPAI_GRADE_OF_RESPONSE (optional) | RESOLVED   |

  Table 14: n8n Webhook Integration Points

  | Trigger                     | Webhook Endpoint                | Data Sent                                   | n8n Action
            | Data Returned                     | Saved To Field                   |
  |-----------------------------|---------------------------------|---------------------------------------------|------------------------------------------------------------------------------------------
  ----------|-----------------------------------|----------------------------------|
  | Employee submits escalation | /webhook/escalation-ai-analysis | {task_id, property_link}                    | 1. Fetch task tree from ClickUp2. Fetch property vector store3. Analyze SOPs4. Generate
  suggestion | {ai_suggestion: "text"}           | AI_SUGGESTIONAI_SOLUTION_DISPLAY |
  | Supervisor answers          | /webhook/grade-response         | {task_id, supervisor_answer, ai_suggestion} | 1. Compare supervisor answer to AI suggestion2. Evaluate against SOPs3. Generate
  grade/feedback    | {grade: "text", feedback: "text"} | AI_GRADE_OF_RESPONSE             |

  ---
  GAP ANALYSIS: Current → Desired

⏺ Table 15: GAPS - What Needs to Be Built

  | Component                | Current State      | Desired State                                | Gap                                                          | Priority |
  |--------------------------|--------------------|----------------------------------------------|--------------------------------------------------------------|----------|
  | States                   | 3 states (0, 1, 2) | 5 states (0, 1, 2, 3, 4)                     | Need 2 new states:- AWAITING_INFO (3)- ESCALATED_LEVEL_2 (4) | HIGH     |
  | Property Link Validation | None               | Pre-escalation check + auto-copy from parent | CRITICAL: Must block escalation if no property link          | CRITICAL |
  | AI Suggestion            | None               | n8n integration for AI analysis              | Need n8n webhook integration                                 | HIGH     |
  | AI Grading               | None               | n8n grades supervisor responses              | Need n8n webhook integration                                 | MEDIUM   |
  | RFI System               | None               | Complete RFI request/response flow           | Need 3 new endpoints + UI                                    | HIGH     |
  | Level 2 Escalation       | None               | Escalate to Christian only                   | Need endpoint + routing logic                                | HIGH     |
  | Multi-action UI          | 1 action (respond) | 3 actions (answer/RFI/escalate)              | Need UI redesign for supervisor view                         | HIGH     |
  | Escalation History       | None               | Track all state transitions                  | Need new field + logging                                     | MEDIUM   |

  Table 16: NEW Custom Fields Checklist

  | Field Name               | ClickUp ID      | Type                                         | Where to Add in ClickUp | Default Value                                     |
  |--------------------------|-----------------|----------------------------------------------|-------------------------|---------------------------------------------------|
  | PROPERTY_LINK            | Check if exists | Task Relationship                            | Process Library tasks   | None                                              |
  | AI_SUGGESTION            | CREATE NEW      | Long Text                                    | Process Library tasks   | Empty                                             |
  | AI_SOLUTION_DISPLAY      | CREATE NEW      | Long Text                                    | Process Library tasks   | Empty                                             |
  | AI_GRADE_OF_RESPONSE     | CREATE NEW      | Long Text                                    | Process Library tasks   | Empty                                             |
  | ESCALATION_LEVEL         | CREATE NEW      | Dropdown (1=Supervisor, 2=Christian)         | Process Library tasks   | 1                                                 |
  | RFI_STATUS               | CREATE NEW      | Dropdown (None, Active, Responded, Resolved) | Process Library tasks   | None                                              |
  | RFI_REQUEST              | CREATE NEW      | Long Text                                    | Process Library tasks   | Empty                                             |
  | RFI_RESPONSE             | CREATE NEW      | Long Text                                    | Process Library tasks   | Empty                                             |
  | ESCALATION_HISTORY       | CREATE NEW      | Long Text (JSON array)                       | Process Library tasks   | []                                                |
  | Update ESCALATION_STATUS | Existing        | Dropdown                                     | Add 2 new options       | Add: "Awaiting Info" (3), "Escalated Level 2" (4) |

  Table 17: NEW Backend Endpoints Checklist

  | Endpoint                                          | Status                                  | Dependencies                     | Complexity |
  |---------------------------------------------------|-----------------------------------------|----------------------------------|------------|
  | /api/task-helper/validate-property-link/<task_id> | ❌ NEW                                   | ClickUp API                      | LOW        |
  | /api/task-helper/escalate-with-ai/<task_id>       | ❌ NEW                                   | n8n webhook, property validation | HIGH       |
  | /api/task-helper/supervisor-answer/<task_id>      | ⚠️ MODIFY existing /supervisor-response | n8n webhook for grading          | MEDIUM     |
  | /api/task-helper/request-info/<task_id>           | ❌ NEW                                   | ClickUp comment API              | MEDIUM     |
  | /api/task-helper/respond-to-rfi/<task_id>         | ❌ NEW                                   | None                             | LOW        |
  | /api/task-helper/escalate-to-level-2/<task_id>    | ❌ NEW                                   | None                             | LOW        |
  | /api/task-helper/christian-answer/<task_id>       | ❌ NEW                                   | Optional n8n grading             | LOW        |

  Table 18: NEW Frontend Components Checklist

  | Component             | Location                            | Status | Purpose                                       |
  |-----------------------|-------------------------------------|--------|-----------------------------------------------|
  | PropertyLinkValidator | Before escalation form              | ❌ NEW  | Check property link exists, show error if not |
  | AISuggestionDisplay   | After escalation submitted          | ❌ NEW  | Display AI's suggested solution to employee   |
  | SupervisorActionPanel | Supervisor view                     | ❌ NEW  | 3-button UI: Answer / Request Info / Escalate |
  | RFIRequestForm        | Supervisor view                     | ❌ NEW  | Text input for info request                   |
  | RFIResponseForm       | Employee view (AWAITING_INFO state) | ❌ NEW  | Text input for RFI response                   |
  | Level2EscalationForm  | Supervisor view                     | ❌ NEW  | Pre-populated reason + additional context     |
  | EscalationHistoryLog  | All views                           | ❌ NEW  | Shows timeline of state changes               |
  | AIGradeDisplay        | Resolved view                       | ❌ NEW  | Shows AI's evaluation of supervisor response  |

  ---
  IMPLEMENTATION PLAN - Phased Approach

⏺ PHASE 1: Foundation (CRITICAL - Must Do First)

  | Order | Task                                  | File                        | Details                                           | Blocks                   |
  |-------|---------------------------------------|-----------------------------|---------------------------------------------------|--------------------------|
  | 1.1   | Create new custom fields in ClickUp   | ClickUp UI                  | All 9 new fields from Table 16                    | Everything               |
  | 1.2   | Update ESCALATION_STATUS dropdown     | ClickUp UI                  | Add options 3 & 4                                 | State detection          |
  | 1.3   | Add property link validation endpoint | app_secure.py               | /api/task-helper/validate-property-link/<task_id> | Escalation flow          |
  | 1.4   | Update frontend field IDs constant    | escalation-v2.html line 176 | Add all new field IDs                             | Frontend state detection |

  Dependencies: None - Start hereTesting: Verify fields exist, can be read/written via API

  ---
  PHASE 2: Property Link Validation (CRITICAL)

  | Order | Task                                   | File               | Details                                                 | Blocks                |
  |-------|----------------------------------------|--------------------|---------------------------------------------------------|-----------------------|
  | 2.1   | Build property link check logic        | app_secure.py      | Check task → check parent → return result               | n8n integration       |
  | 2.2   | Build property link auto-copy logic    | app_secure.py      | If subtask missing, copy from parent                    | n8n integration       |
  | 2.3   | Add frontend pre-escalation validator  | escalation-v2.html | Call validation endpoint before showing form            | Escalation submission |
  | 2.4   | Add error UI for missing property link | escalation-v2.html | "This task must have a property link before escalation" | User experience       |

  Dependencies: Phase 1 completeTesting: Test with task that has no property link, test with subtask that inherits from parent

  ---
  PHASE 3: n8n AI Suggestion Integration (HIGH PRIORITY)

  | Order | Task                                    | File               | Details                                                 | Blocks                   |
  |-------|-----------------------------------------|--------------------|---------------------------------------------------------|--------------------------|
  | 3.1   | Create n8n webhook: escalation analysis | n8n                | Receives task_id + property_link, returns AI suggestion | AI suggestion display    |
  | 3.2   | Update escalation endpoint              | app_secure.py      | Replace /escalate with /escalate-with-ai                | Full flow                |
  | 3.3   | Add n8n webhook call in backend         | app_secure.py      | POST to n8n with task_id + property_link                | AI suggestion            |
  | 3.4   | Save AI suggestion to custom fields     | app_secure.py      | Set AI_SUGGESTION + AI_SOLUTION_DISPLAY                 | Display                  |
  | 3.5   | Add AI suggestion display component     | escalation-v2.html | Show AI suggestion to employee after submission         | Employee sees suggestion |

  Dependencies: Phase 2 complete (property link must exist)Testing: Submit escalation, verify n8n receives data, verify AI suggestion saves and displays

  ---
  PHASE 4: Supervisor Multi-Action UI (HIGH PRIORITY)

  | Order | Task                                     | File                        | Details                                                | Blocks             |
  |-------|------------------------------------------|-----------------------------|--------------------------------------------------------|--------------------|
  | 4.1   | Update state detection for new states    | escalation-v2.html line 485 | Add AWAITING_INFO & ESCALATED_LEVEL_2 detection        | UI rendering       |
  | 4.2   | Create supervisor action panel component | escalation-v2.html          | 3 buttons: Answer / Request Info / Escalate to Level 2 | Supervisor actions |
  | 4.3   | Add supervisor answer endpoint           | app_secure.py               | /api/task-helper/supervisor-answer/<task_id>           | Answer flow        |
  | 4.4   | Add request info endpoint                | app_secure.py               | /api/task-helper/request-info/<task_id>                | RFI flow           |
  | 4.5   | Add escalate to level 2 endpoint         | app_secure.py               | /api/task-helper/escalate-to-level-2/<task_id>         | Level 2 flow       |

  Dependencies: Phase 1 completeTesting: Supervisor can see 3 options, each triggers correct endpoint

  ---
  PHASE 5: RFI (Request for Info) System (HIGH PRIORITY)

  | Order | Task                                     | File               | Details                                      | Blocks             |
  |-------|------------------------------------------|--------------------|----------------------------------------------|--------------------|
  | 5.1   | Create RFI request form component        | escalation-v2.html | Supervisor enters what info they need        | RFI submission     |
  | 5.2   | Create AWAITING_INFO state UI            | escalation-v2.html | Employee sees RFI request + response form    | Employee response  |
  | 5.3   | Add RFI response endpoint                | app_secure.py      | /api/task-helper/respond-to-rfi/<task_id>    | Back to supervisor |
  | 5.4   | Update state to route back to supervisor | app_secure.py      | Set ESCALATION_STATUS = 1 after RFI response | Supervisor review  |

  Dependencies: Phase 4 completeTesting: Supervisor requests info → employee sees request → employee responds → routes back to supervisor

  ---
  PHASE 6: Level 2 Escalation (HIGH PRIORITY)

  | Order | Task                              | File               | Details                                               | Blocks               |
  |-------|-----------------------------------|--------------------|-------------------------------------------------------|----------------------|
  | 6.1   | Create level 2 escalation form    | escalation-v2.html | Pre-populate AI response, allow editing               | Submission           |
  | 6.2   | Add Christian answer endpoint     | app_secure.py      | /api/task-helper/christian-answer/<task_id>           | Christian resolution |
  | 6.3   | Create ESCALATED_LEVEL_2 state UI | escalation-v2.html | Shows escalation details + action panel for Christian | Christian sees it    |
  | 6.4   | Update field: ESCALATION_LEVEL    | app_secure.py      | Set to 2 when escalating to Christian                 | Tracking             |

  Dependencies: Phase 4 completeTesting: Supervisor escalates to level 2 → Christian sees it → Christian can answer

  ---
  PHASE 7: AI Grading Integration (MEDIUM PRIORITY)

  | Order | Task                               | File               | Details                                                   | Blocks        |
  |-------|------------------------------------|--------------------|-----------------------------------------------------------|---------------|
  | 7.1   | Create n8n webhook: grade response | n8n                | Receives supervisor answer + AI suggestion, returns grade | Grade display |
  | 7.2   | Update supervisor answer endpoint  | app_secure.py      | Call n8n webhook after saving response                    | Grade saved   |
  | 7.3   | Save grade to AI_GRADE_OF_RESPONSE | app_secure.py      | Store n8n response                                        | Display       |
  | 7.4   | Add grade display in resolved view | escalation-v2.html | Show AI evaluation of supervisor response                 | Visibility    |

  Dependencies: Phase 3 (n8n setup), Phase 4 (supervisor answer)Testing: Supervisor answers → n8n grades → grade saves → grade displays in UI

  ---
  PHASE 8: History & Logging (MEDIUM PRIORITY)

  | Order | Task                              | File               | Details                                          | Blocks          |
  |-------|-----------------------------------|--------------------|--------------------------------------------------|-----------------|
  | 8.1   | Create state transition logger    | app_secure.py      | Function to append to ESCALATION_HISTORY JSON    | Tracking        |
  | 8.2   | Add logging to all state changes  | app_secure.py      | Call logger on every endpoint that changes state | History         |
  | 8.3   | Create history timeline component | escalation-v2.html | Display state transition history                 | User visibility |

  Dependencies: Phase 1 completeTesting: Perform full escalation → resolve flow, verify history captures all transitions

  ---
  SUMMARY: Implementation Order

  ✅ PHASE 1: Create custom fields + update constants (CRITICAL)
  ✅ PHASE 2: Property link validation (CRITICAL - BLOCKS n8n)
  ✅ PHASE 3: n8n AI suggestion integration (HIGH)
  ✅ PHASE 4: Supervisor multi-action UI (HIGH)
  ✅ PHASE 5: RFI system (HIGH)
  ✅ PHASE 6: Level 2 escalation (HIGH)
  ✅ PHASE 7: AI grading (MEDIUM)
  ✅ PHASE 8: History logging (MEDIUM)

  Estimated Timeline:
  - Phase 1-2: 1 day (foundation)
  - Phase 3: 2 days (n8n integration + testing)
  - Phase 4-6: 3 days (UI + endpoints)
  - Phase 7: 1 day (grading)
  - Phase 8: 1 day (history)

  Total: ~8 days for complete implementation

  ---

⏺ ---
  Does this comprehensive audit and implementation plan look correct?

  I've created:

  1. ✅ 6 Current State tables - Complete documentation of how escalation-v2.html works now
  2. ✅ 9 Desired State tables - Complete specification of your new system
  3. ✅ 5 Gap Analysis tables - Exactly what needs to be built
  4. ✅ 8-Phase Implementation Plan - Concrete build order with dependencies

  Key insights from this analysis:

  - 18 new components to build (9 fields, 7 endpoints, 2 UI states)
  - Critical blocker: Property link validation MUST happen before n8n integration
  - n8n has 2 webhook endpoints: AI suggestion + grading
  - 5 states total instead of current 3
  - Estimated 8 days for full implementation

  Should I proceed with Phase 1 (creating the custom fields specification document for ClickUp)? Or would you like to adjust any part of this plan first?

> yes create phase 1; btw here are some of the ids: 
  1. ESCALATION_REASON (c6e0281e-9001-42d7-a265-8f5da6b71132)
    - Type: Text
    - Set during: Initial escalation
    - Contains: User's explanation of why task needs escalation
  2. ESCALATION_AI_SUMMARY (e9e831f2-b439-4067-8e88-6b715f4263b2)
    - Type: Text
    - Set during: Initial escalation (after AI generation)
    - Contains: AI-generated summary of the escalation context
  3. ESCALATION_STATUS (8d784bd0-18e5-4db3-b45e-9a2900262e04) ⭐
    - Type: Dropdown
    - Values: 0 (Not Escalated), 1 (Escalated), 2 (Resolved)
    - Updated: Initial escalation (0→1), Supervisor response (1→2)
  4. ESCALATED_TO (934811f1-239f-4d53-880c-3655571fd02e)
    - Type: Text/User reference
    - Set during: Initial escalation (optional)
    - Contains: Supervisor/assignee identifier
  5. ESCALATION_TIMESTAMP (5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f)
    - Type: Date with time
    - Set during: Initial escalation
    - Contains: Unix timestamp (ms) when escalation was submitted
  6. SUPERVISOR_RESPONSE (a077ecc9-1a59-48af-b2cd-42a63f5a7f86)
    - Type: Text
    - Set during: Supervisor response submission
    - Contains: Supervisor's resolution response
  7. ESCALATION_RESOLVED_TIMESTAMP (c40bf1c4-7d33-4b2b-8765-0784cd88591a)
    - Type: Date with time
    - Set during: Supervisor response submission
    - Contains: Unix timestamp (ms) when escalation was resolved Escalation_AI_Suggestion: bc5e9359-01cd-408f-adb9-c7bdf1f2dd29 

⏺ Perfect! Let me create Phase 1 with the existing field IDs you've provided.

  PHASE 1: FOUNDATION - Custom Fields Setup

  STEP 1.1: Verify Existing Fields

  ✅ Already Exist (7 fields confirmed):

  | Field Name                    | Field ID                             | Type           | Status   |
  |-------------------------------|--------------------------------------|----------------|----------|
  | ESCALATION_REASON             | c6e0281e-9001-42d7-a265-8f5da6b71132 | Text           | ✅ EXISTS |
  | ESCALATION_AI_SUMMARY         | e9e831f2-b439-4067-8e88-6b715f4263b2 | Text           | ✅ EXISTS |
  | ESCALATION_STATUS             | 8d784bd0-18e5-4db3-b45e-9a2900262e04 | Dropdown       | ✅ EXISTS |
  | ESCALATED_TO                  | 934811f1-239f-4d53-880c-3655571fd02e | Text           | ✅ EXISTS |
  | ESCALATION_TIMESTAMP          | 5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f | Date           | ✅ EXISTS |
  | SUPERVISOR_RESPONSE           | a077ecc9-1a59-48af-b2cd-42a63f5a7f86 | Text           | ✅ EXISTS |
  | ESCALATION_RESOLVED_TIMESTAMP | c40bf1c4-7d33-4b2b-8765-0784cd88591a | Date           | ✅ EXISTS |
  | ESCALATION_AI_SUGGESTION      | bc5e9359-01cd-408f-adb9-c7bdf1f2dd29 | Text (assumed) | ✅ EXISTS |

  ---
  STEP 1.2: Update Existing Dropdown - ESCALATION_STATUS

  Current Options:
  - 0 = "Not Escalated"
  - 1 = "Escalated"
  - 2 = "Resolved"

  ADD These Options:
  - 3 = "Awaiting Info" (RFI state)
  - 4 = "Escalated Level 2" (Christian's queue)

  Action Required:
  1. Go to ClickUp custom field settings
  2. Find ESCALATION_STATUS field
  3. Add option 3: "Awaiting Info"
  4. Add option 4: "Escalated Level 2"

  ---
  STEP 1.3: Create NEW Custom Fields in ClickUp

  Field 1: PROPERTY_LINK (Check if exists first!)

  - Name: Property Link
  - Type: Task Relationship
  - Purpose: Links escalation to property for context
  - Required: Yes (will be enforced in code)
  - Location: Process Library task list
  - Instructions: Search for existing "Property" or "Property Link" field first before creating

  Field 2: AI_SOLUTION_DISPLAY

  - Name: AI Solution Display
  - Type: Long Text
  - Purpose: Shows AI's suggested solution to employee
  - Default: Empty
  - Location: Process Library task list

  Field 3: AI_GRADE_OF_RESPONSE

  - Name: AI Grade of Response
  - Type: Long Text
  - Purpose: AI's evaluation of supervisor's answer
  - Default: Empty
  - Location: Process Library task list

  Field 4: ESCALATION_LEVEL

  - Name: Escalation Level
  - Type: Dropdown
  - Options:
    - 1 = "Supervisor" (default)
    - 2 = "Christian"
  - Default: 1
  - Location: Process Library task list

  Field 5: RFI_STATUS

  - Name: RFI Status
  - Type: Dropdown
  - Options:
    - 0 = "None" (default)
    - 1 = "Active"
    - 2 = "Responded"
    - 3 = "Resolved"
  - Default: 0 (None)
  - Location: Process Library task list

  Field 6: RFI_REQUEST

  - Name: RFI Request
  - Type: Long Text
  - Purpose: What information supervisor is requesting
  - Default: Empty
  - Location: Process Library task list

  Field 7: RFI_RESPONSE

  - Name: RFI Response
  - Type: Long Text
  - Purpose: Employee's response to information request
  - Default: Empty
  - Location: Process Library task list

  Field 8: ESCALATION_HISTORY

  - Name: Escalation History
  - Type: Long Text
  - Purpose: JSON log of all state transitions
  - Default: "[]"
  - Location: Process Library task list
  - Note: Will store JSON array like [{"timestamp": 123, "from": "NOT_ESCALATED", "to": "ESCALATED_LEVEL_1", "by": "user@email"}]

  ---
  STEP 1.4: Update Frontend Constants

  Now I'll update the escalation-v2.html file with all field IDs:
