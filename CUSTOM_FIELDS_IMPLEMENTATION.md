# Custom Fields Implementation Documentation

## Custom Field Impact Matrix

| Field Name | Field ID | Trigger | Where Set | Impact When SET | Impact When NOT SET | User Experience |
|------------|----------|---------|-----------|-----------------|---------------------|-----------------|
| ESCALATION_REASON | c6e0281e-9001-42d7-a265-8f5da6b71132 | User submits escalation | `/api/task-helper/escalate/{task_id}` | Shows user's reason in UI, enables supervisor visibility | No context for escalation | Without: Supervisor has no context. With: Clear understanding of issue |
| ESCALATION_AI_SUMMARY | e9e831f2-b439-4067-8e88-6b715f4263b2 | AI generates summary during escalation | `/api/task-helper/escalate/{task_id}` | Provides AI analysis for quick understanding | Manual review required | Without: Time-consuming manual review. With: Instant AI insights |
| ESCALATION_STATUS | 8d784bd0-18e5-4db3-b45e-9a2900262e04 | Escalation submit OR Supervisor response | Both endpoints | Controls UI state (Escalated/Resolved) | Task shows as normal, no escalation UI | Without: No escalation workflow visible. With: Clear state indicators |
| ESCALATION_TIMESTAMP | 5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f | User submits escalation | `/api/task-helper/escalate/{task_id}` | Shows when escalated, enables time tracking | No escalation time tracking | Without: No audit trail. With: Complete timeline |
| ESCALATED_TO | 934811f1-239f-4d53-880c-3655571fd02e | User selects supervisor (optional) | `/api/task-helper/escalate/{task_id}` | Routes to specific supervisor | General escalation pool | Without: Generic routing. With: Direct assignment |
| SUPERVISOR_RESPONSE | a077ecc9-1a59-48af-b2cd-42a63f5a7f86 | Supervisor submits response | `/api/task-helper/supervisor-response/{task_id}` | Shows resolution in UI | No response visible | Without: Unresolved state. With: Clear resolution |
| ESCALATION_RESOLVED_TIMESTAMP | c40bf1c4-7d33-4b2b-8765-0784cd88591a | Supervisor submits response | `/api/task-helper/supervisor-response/{task_id}` | Shows resolution time, calculates SLA | No resolution tracking | Without: No SLA metrics. With: Performance tracking |

## Code Implementation Proof

### 1. ESCALATION_REASON (c6e0281e-9001-42d7-a265-8f5da6b71132)
**Trigger:** User types reason and clicks "Submit Escalation"

```python
# backend/app_secure.py - Lines 774-780
# Setting ESCALATION_REASON field
reason_field_id = escalation_fields.get('ESCALATION_REASON')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{reason_field_id}',
    headers=headers,
    json={'value': reason}
)
logger.info(f"Set ESCALATION_REASON: {clickup_response.status_code}")
```

### 2. ESCALATION_AI_SUMMARY (e9e831f2-b439-4067-8e88-6b715f4263b2)
**Trigger:** Generated after user submits escalation

```python
# backend/app_secure.py - Lines 782-788
# Setting ESCALATION_AI_SUMMARY field
summary_field_id = escalation_fields.get('ESCALATION_AI_SUMMARY')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{summary_field_id}',
    headers=headers,
    json={'value': ai_summary}
)
logger.info(f"Set ESCALATION_AI_SUMMARY: {clickup_response.status_code}")
```

### 3. ESCALATION_STATUS (8d784bd0-18e5-4db3-b45e-9a2900262e04)
**Trigger:** Set to "Escalated" on escalation, "Resolved" on supervisor response

```python
# backend/app_secure.py - Lines 790-797
# Setting to "Escalated" during escalation
status_field_id = escalation_fields.get('ESCALATION_STATUS')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{status_field_id}',
    headers=headers,
    # UUID for 'Escalated' dropdown option
    json={'value': '8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497'}
)
logger.info(f"Set ESCALATION_STATUS to Escalated: {clickup_response.status_code}")

# backend/app_secure.py - Lines 906-913
# Setting to "Resolved" during supervisor response
status_field_id = escalation_fields.get('ESCALATION_STATUS')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{status_field_id}',
    headers=headers,
    # UUID for 'Resolved' dropdown option
    json={'value': 'cbf82936-5488-4612-93a7-f8161071b0eb'}
)
logger.info(f"Set ESCALATION_STATUS to Resolved: {clickup_response.status_code}")
```

### 4. ESCALATION_TIMESTAMP (5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f)
**Trigger:** Set when escalation is submitted

```python
# backend/app_secure.py - Lines 799-808
# Setting ESCALATION_TIMESTAMP field
timestamp_field_id = escalation_fields.get('ESCALATION_TIMESTAMP')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{timestamp_field_id}',
    headers=headers,
    json={
        'value': int(datetime.now().timestamp() * 1000),
        'value_options': {'time': True}
    }
)
logger.info(f"Set ESCALATION_TIMESTAMP: {clickup_response.status_code}")
```

### 5. ESCALATED_TO (934811f1-239f-4d53-880c-3655571fd02e)
**Trigger:** Optional - when user selects a specific supervisor

```python
# backend/app_secure.py - Lines 810-820
# Setting ESCALATED_TO field (if supervisor selected)
if escalated_to:
    escalated_to_field_id = escalation_fields.get('ESCALATED_TO')
    try:
        clickup_response = requests.post(
            f'https://api.clickup.com/api/v2/task/{task_id}/field/{escalated_to_field_id}',
            headers=headers,
            json={'value': escalated_to}
        )
        logger.info(f"Set ESCALATED_TO: {clickup_response.status_code}")
    except Exception as e:
        logger.warning(f"Could not set ESCALATED_TO (field may not exist): {e}")
```

### 6. SUPERVISOR_RESPONSE (a077ecc9-1a59-48af-b2cd-42a63f5a7f86)
**Trigger:** Supervisor types response and clicks "Submit Response"

```python
# backend/app_secure.py - Lines 897-904
# Setting SUPERVISOR_RESPONSE field
response_field_id = escalation_fields.get('SUPERVISOR_RESPONSE')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{response_field_id}',
    headers=headers,
    json={'value': response}
)
logger.info(f"Set SUPERVISOR_RESPONSE: {clickup_response.status_code}")
```

### 7. ESCALATION_RESOLVED_TIMESTAMP (c40bf1c4-7d33-4b2b-8765-0784cd88591a)
**Trigger:** Set when supervisor submits response

```python
# backend/app_secure.py - Lines 915-924
# Setting ESCALATION_RESOLVED_TIMESTAMP field
resolved_timestamp_field_id = escalation_fields.get('ESCALATION_RESOLVED_TIMESTAMP')
clickup_response = requests.post(
    f'https://api.clickup.com/api/v2/task/{task_id}/field/{resolved_timestamp_field_id}',
    headers=headers,
    json={
        'value': int(datetime.now().timestamp() * 1000),
        'value_options': {'time': True}
    }
)
logger.info(f"Set ESCALATION_RESOLVED_TIMESTAMP: {clickup_response.status_code}")
```

## Frontend State Detection Based on Custom Fields

The frontend uses these fields to determine the current state and show appropriate UI:

```javascript
// backend/templates/secured/task-helper.html - Lines 243-246
// State detection logic
const isEscalated = task.custom_fields?.find(f => 
    f.id === CUSTOM_FIELDS.ESCALATION_STATUS)?.value === 'Escalated';
const isResolved = task.custom_fields?.find(f => 
    f.id === CUSTOM_FIELDS.ESCALATION_STATUS)?.value === 'Resolved';
```

## User Journey Impact

### Normal State (No fields set)
- User sees: Task details, "Generate AI Summary" button, escalation form
- Available actions: Can escalate task
- Hidden: Supervisor response section

### Escalated State (ESCALATION_STATUS = "Escalated")
- User sees: Escalation details, reason, AI summary, timestamp
- Available actions: Supervisor can respond
- Hidden: Escalation form (already escalated)

### Resolved State (ESCALATION_STATUS = "Resolved")
- User sees: Complete history - escalation, supervisor response, timestamps
- Available actions: View-only, can re-escalate if needed
- Hidden: Both forms (already resolved)

## Critical Implementation Notes

1. **API Endpoint:** Must use `/task/{task_id}/field/{field_id}` for individual field updates
2. **Dropdown Values:** ESCALATION_STATUS requires UUID values, not text
   - "Escalated" = "8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497"
   - "Resolved" = "cbf82936-5488-4612-93a7-f8161071b0eb"
3. **Date Fields:** Require millisecond timestamps with `value_options: {time: true}`
4. **Field Availability:** ESCALATED_TO may not exist on all task lists (handle gracefully)