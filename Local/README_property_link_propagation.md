# Property Link Propagation Test

## Overview
This test function demonstrates how to navigate ClickUp task structure and propagate the `property_link` custom field from parent tasks to subtasks when missing.

## Task Structure Analysis

### Sample Task (TICKET-65711)
```
Task ID: 868fg1umj
Task Name: Repair bathroom fans in En-Suite Master Bedroom-Guest Commitment
Parent ID: 868fjz57q
Top Level Parent ID: 868fjz57q
Property Link: [] (EMPTY)
```

### Parent Task (868fjz57q)
```
Task Name: Fix chipped tub and replace exhaust fan-AI
Property Link: [{
    'id': '868ckm4qz',
    'name': '52_palomar',
    'status': 'to do',
    'custom_type': 1002,
    'url': 'https://app.clickup.com/t/868ckm4qz'
}]
```

## Key Findings

### 1. Property Link Custom Field Structure
- **Field ID**: `73999194-0433-433d-a27c-4d9c5f194fd0`
- **Type**: `tasks` (relationship field linking to other tasks)
- **Value Format**: Array of task objects with metadata
- **Empty State**: Empty array `[]` when not set

### 2. Task Hierarchy Navigation
- Tasks have `parent` field pointing to immediate parent
- Tasks have `top_level_parent` field pointing to root parent
- For subtasks, both fields point to same parent in our test case

### 3. Property Link Propagation Logic

```python
def propagate_property_link(task_id):
    1. Fetch task using GET /api/v2/task/{task_id}
    2. Check custom_fields array for property_link (id: 73999194-0433-433d-a27c-4d9c5f194fd0)
    3. If value is None/[]/empty:
       a. Get parent_id from task.parent or task.top_level_parent
       b. Fetch parent task using GET /api/v2/task/{parent_id}
       c. Extract property_link value from parent
       d. If parent has property_link:
          - Set on subtask using POST /api/v2/task/{task_id}/field/{field_id}
          - Payload: {"value": parent_property_link_value}
```

## Test Results

### Dry Run Output
```
✅ Parent has property_link: [{'id': '868ckm4qz', 'name': '52_palomar', ...}]
🔍 DRY RUN: Would set property_link to [{'id': '868ckm4qz', 'name': '52_palomar', ...}]
```

### API Endpoints Used

1. **Get Task**: `GET /api/v2/task/{task_id}?custom_task_ids=true&team_id=9011954126`
2. **Get Parent**: `GET /api/v2/task/{parent_id}?team_id=9011954126`
3. **Set Custom Field**: `POST /api/v2/task/{task_id}/field/{field_id}` with `{"value": [...]}`

## Implementation Notes

### For Backend Integration (`app_secure.py`)

1. **Add this function before escalation processing**:
```python
def ensure_property_link(task_id: str) -> Optional[List[Dict]]:
    """
    Ensure task has property_link, propagate from parent if missing.
    Returns the property_link value (from task or parent).
    """
    # Fetch task
    task = get_clickup_task(task_id)

    # Check for property_link
    property_link = get_custom_field(task, FIELD_IDS['PROPERTY_LINK'])

    if property_link:
        return property_link

    # Get parent
    parent_id = task.get('parent') or task.get('top_level_parent')
    if not parent_id:
        return None

    parent_task = get_clickup_task(parent_id)
    parent_property_link = get_custom_field(parent_task, FIELD_IDS['PROPERTY_LINK'])

    if parent_property_link:
        # Set on subtask
        set_custom_field(task_id, FIELD_IDS['PROPERTY_LINK'], parent_property_link)
        return parent_property_link

    return None
```

2. **Call before sending webhook to n8n**:
```python
@app.route('/api/task-helper/escalate/<task_id>', methods=['POST'])
def escalate_task(task_id):
    # CRITICAL: Ensure property_link is set before sending to n8n
    property_link = ensure_property_link(task_id)

    if not property_link:
        logger.warning(f"No property_link found for task {task_id}")

    # Now send to n8n with property_link guaranteed to be set
    webhook_payload = {
        'task_id': task_id,
        'property_link': property_link,
        'escalation_reason': ...,
        # ... rest of payload
    }
```

## Environment Setup

### Required Environment Variable
```bash
export CLICKUP_API_KEY="your_api_key_with_write_permissions"
```

### Run Test
```bash
cd /Users/AIRBNB/Task-Specific-Pages/Local
python3 test_property_link_propagation.py
```

## Next Steps for Escalation System

1. ✅ **Property Link Detection** - COMPLETED
2. ✅ **Parent Navigation** - COMPLETED
3. ✅ **Propagation Logic** - COMPLETED
4. ⏳ **Integrate into Backend** - PENDING
5. ⏳ **Add to Escalation Endpoint** - PENDING
6. ⏳ **Send to n8n with Property Context** - PENDING
7. ⏳ **AI Analysis with Property Vector Store** - PENDING

## Files Created

- `/Local/test_property_link_propagation.py` - Main test function
- `/Local/sample_task_response.json` - Sample API response for analysis
- `/Local/README_property_link_propagation.md` - This documentation
