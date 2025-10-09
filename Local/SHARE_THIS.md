# Property Link Propagation - For Backend Integration

## Key Function

```python
def ensure_property_link(task_id: str, clickup_token: str, team_id: str = '9011954126') -> Optional[List[str]]:
    """
    Ensure task has property_link, propagate from parent if missing.
    
    Args:
        task_id: Task ID (can be custom like TICKET-65711 or regular like 868fg1umj)
        clickup_token: ClickUp API token
        team_id: ClickUp team/workspace ID
        
    Returns:
        List of property link task IDs, or None if not found
    """
    import requests
    
    PROPERTY_LINK_FIELD_ID = '73999194-0433-433d-a27c-4d9c5f194fd0'
    BASE_URL = 'https://api.clickup.com/api/v2'
    headers = {'Authorization': clickup_token, 'Content-Type': 'application/json'}
    
    # Helper: Detect if custom task ID
    def is_custom_id(tid):
        return 'TICKET' in tid.upper() or '-' in tid or tid[0].isupper()
    
    # Helper: Get custom field value
    def get_field(task, field_id):
        for field in task.get('custom_fields', []):
            if field['id'] == field_id:
                value = field.get('value')
                if value and value != []:
                    return value
        return None
    
    # Step 1: Get task
    params = {'team_id': team_id}
    if is_custom_id(task_id):
        params['custom_task_ids'] = 'true'
    
    response = requests.get(f'{BASE_URL}/task/{task_id}', headers=headers, params=params)
    response.raise_for_status()
    task = response.json()
    task_regular_id = task['id']  # Always get regular ID for POST requests
    
    # Step 2: Check if property_link exists
    property_link = get_field(task, PROPERTY_LINK_FIELD_ID)
    if property_link:
        # Extract just the IDs
        return [p['id'] for p in property_link]
    
    # Step 3: Get parent task
    parent_id = task.get('parent') or task.get('top_level_parent')
    if not parent_id:
        return None
    
    # Step 4: Get parent's property_link
    parent_response = requests.get(
        f'{BASE_URL}/task/{parent_id}',
        headers=headers,
        params={'team_id': team_id}
    )
    parent_response.raise_for_status()
    parent_task = parent_response.json()
    
    parent_property_link = get_field(parent_task, PROPERTY_LINK_FIELD_ID)
    if not parent_property_link:
        return None
    
    # Step 5: Extract IDs and set on subtask
    property_link_ids = [p['id'] for p in parent_property_link]
    
    # CRITICAL: Use regular task ID, not custom ID
    # Payload format: {"value": {"add": [task_ids]}}
    set_response = requests.post(
        f'{BASE_URL}/task/{task_regular_id}/field/{PROPERTY_LINK_FIELD_ID}',
        headers=headers,
        json={'value': {'add': property_link_ids}}
    )
    set_response.raise_for_status()
    
    return property_link_ids
```

## Integration into Backend

**File:** `app_secure.py`  
**Location:** In `escalate_task()` function, BEFORE line 744

```python
@app.route('/api/task-helper/escalate/<task_id>', methods=['POST'])
def escalate_task(task_id):
    # ... existing code ...
    
    # Get ClickUp API configuration
    clickup_token = os.getenv('CLICKUP_API_KEY')
    
    # CRITICAL: Ensure property_link is set before sending to n8n
    try:
        property_link_ids = ensure_property_link(task_id, clickup_token)
        if property_link_ids:
            logger.info(f"Property link set/verified for {task_id}: {property_link_ids}")
        else:
            logger.warning(f"No property_link found for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to ensure property_link: {e}")
        property_link_ids = None
    
    # ... continue with escalation fields update ...
```

## Key Points

1. **Detects custom task IDs** - Checks for TICKET prefix, hyphens, or uppercase
2. **Uses regular ID for POST** - Critical! POST requests don't support custom_task_ids parameter
3. **Correct payload format** - `{"value": {"add": [task_ids]}}` for Task Relationship fields
4. **Extracts only IDs** - Not full task objects, just the ID strings
5. **Returns IDs for n8n** - Can be included in webhook payload

## Tested & Verified

✅ Successfully set property_link on TICKET-65711  
✅ Propagated from parent task 868fjz57q  
✅ Property: 52_palomar (868ckm4qz)

## Full Implementation

For complete code with error handling, logging, and testing utilities, see:
`/Users/AIRBNB/Task-Specific-Pages/Local/test_property_link_propagation.py`
