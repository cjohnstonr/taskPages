#!/usr/bin/env python3
"""
Test function to propagate property_link from parent task to subtask if missing.

Logic:
1. Get task response for given task ID
2. Check if property_link custom field exists and has value
3. If missing/empty, get parent task ID from task structure
4. Fetch parent task
5. Extract property_link from parent
6. Set property_link on subtask using ClickUp API
"""

import os
import requests
import json
from typing import Optional, Dict, Any, List

# ClickUp Configuration
CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY', 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB')
TEAM_ID = '9011954126'
PROPERTY_LINK_FIELD_ID = '73999194-0433-433d-a27c-4d9c5f194fd0'

BASE_URL = 'https://api.clickup.com/api/v2'
HEADERS = {
    'Authorization': CLICKUP_API_KEY,
    'Content-Type': 'application/json'
}


def is_custom_task_id(task_id: str) -> bool:
    """
    Detect if task_id is a custom ID format (e.g., TICKET-65711).

    Custom IDs typically contain uppercase prefixes like TICKET, TASK, etc.

    Args:
        task_id: Task ID to check

    Returns:
        True if custom ID format, False if regular ID
    """
    # Check if it contains common custom ID patterns
    # Custom IDs have format like: TICKET-12345, TASK-123, etc.
    # Regular IDs are lowercase alphanumeric like: 868fg1umj
    return 'TICKET' in task_id.upper() or '-' in task_id or task_id[0].isupper()


def get_task(task_id: str, use_custom_id: bool = None) -> Dict[str, Any]:
    """
    Fetch task from ClickUp API.

    Args:
        task_id: Task ID (can be custom_id like TICKET-65711 or regular ID)
        use_custom_id: Whether to use custom_task_ids parameter.
                      If None, auto-detects based on task_id format.

    Returns:
        Task data as dict

    IMPORTANT: When using custom task IDs (like TICKET-65711):
    - MUST include custom_task_ids=true parameter
    - MUST include team_id parameter
    - For regular IDs, these parameters are optional
    """
    params = {'team_id': TEAM_ID}

    # Auto-detect custom ID if not specified
    if use_custom_id is None:
        use_custom_id = is_custom_task_id(task_id)

    if use_custom_id:
        params['custom_task_ids'] = 'true'

    url = f'{BASE_URL}/task/{task_id}'
    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_custom_field_value(task: Dict[str, Any], field_id: str) -> Optional[Any]:
    """
    Extract custom field value from task.

    Args:
        task: Task data dict
        field_id: Custom field ID to search for

    Returns:
        Field value or None if not found
    """
    custom_fields = task.get('custom_fields', [])
    for field in custom_fields:
        if field['id'] == field_id:
            value = field.get('value')
            # Check if value is empty list/None/empty string
            if value is None or value == [] or value == '':
                return None
            return value
    return None


def get_parent_task_id(task: Dict[str, Any]) -> Optional[str]:
    """
    Extract parent task ID from task structure.

    Args:
        task: Task data dict

    Returns:
        Parent task ID or None if no parent
    """
    # Try parent first, then top_level_parent
    parent_id = task.get('parent')
    if not parent_id:
        parent_id = task.get('top_level_parent')
    return parent_id


def set_custom_field(task_id: str, field_id: str, value: Any) -> Dict[str, Any]:
    """
    Set custom field value on a task.

    Args:
        task_id: Task ID (MUST be regular ID, not custom_id)
        field_id: Custom field ID
        value: Value to set (for tasks-type fields, should be list of task IDs as strings)

    Returns:
        API response as dict

    IMPORTANT:
    - ClickUp API does NOT accept custom_task_ids parameter for POST requests
    - Must use regular task ID (not TICKET-xxxxx format)
    - For Task Relationship fields (type: "tasks"), value must be array of task IDs
      Example: {"value": {"add": ["868ckm4qz"]}}
    """
    url = f'{BASE_URL}/task/{task_id}/field/{field_id}'

    # For tasks-type fields, value should be {"add": [task_ids]}
    payload = {'value': value}

    response = requests.post(url, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


def propagate_property_link(task_id: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Main function to propagate property_link from parent to subtask if missing.

    Args:
        task_id: Task ID to check (can be custom_id or regular ID)
        dry_run: If True, only report what would happen without making changes

    Returns:
        Dict with operation results
    """
    result = {
        'task_id': task_id,
        'task_name': None,
        'has_property_link': False,
        'parent_task_id': None,
        'parent_has_property_link': False,
        'property_link_value': None,
        'action_taken': None,
        'success': False,
        'error': None
    }

    try:
        # Step 1: Get the task
        print(f"\n📋 Fetching task: {task_id}")
        task = get_task(task_id)
        result['task_name'] = task['name']
        task_regular_id = task['id']  # Store regular ID for API calls

        print(f"   Task Name: {task['name']}")
        print(f"   Regular ID: {task_regular_id}")

        # Step 2: Check if property_link exists on this task
        property_link = get_custom_field_value(task, PROPERTY_LINK_FIELD_ID)

        if property_link:
            result['has_property_link'] = True
            result['property_link_value'] = property_link
            result['action_taken'] = 'none_needed'
            result['success'] = True
            print(f"✅ Task already has property_link: {property_link}")
            return result

        print("⚠️  Task is missing property_link")

        # Step 3: Get parent task ID
        parent_id = get_parent_task_id(task)

        if not parent_id:
            result['action_taken'] = 'no_parent'
            result['error'] = 'Task has no parent task'
            print("❌ Task has no parent task to inherit property_link from")
            return result

        result['parent_task_id'] = parent_id
        print(f"📌 Parent task ID: {parent_id}")

        # Step 4: Fetch parent task
        print(f"📋 Fetching parent task: {parent_id}")
        parent_task = get_task(parent_id, use_custom_id=False)  # Use regular ID
        print(f"   Parent Name: {parent_task['name']}")

        # Step 5: Check if parent has property_link
        parent_property_link = get_custom_field_value(parent_task, PROPERTY_LINK_FIELD_ID)

        if not parent_property_link:
            result['action_taken'] = 'parent_missing'
            result['error'] = 'Parent task also missing property_link'
            print("❌ Parent task also missing property_link - cannot propagate")
            return result

        result['parent_has_property_link'] = True
        result['property_link_value'] = parent_property_link
        print(f"✅ Parent has property_link: {parent_property_link}")

        # Step 6: Extract task IDs from parent_property_link
        # parent_property_link is array of task objects with 'id' field
        # We need just the IDs for the API call
        property_link_ids = [task_obj['id'] for task_obj in parent_property_link]
        print(f"📝 Extracted property link IDs: {property_link_ids}")

        # Step 7: Set property_link on subtask
        if dry_run:
            result['action_taken'] = 'dry_run'
            result['success'] = True
            print(f"🔍 DRY RUN: Would set property_link")
            print(f"   Task IDs to add: {property_link_ids}")
            print(f"   Using regular task ID: {task_regular_id} (not custom_id)")
        else:
            print(f"🔧 Setting property_link on subtask...")
            print(f"   Using regular task ID: {task_regular_id}")
            print(f"   Property IDs to add: {property_link_ids}")
            print(f"   NOTE: POST requests do NOT support custom_task_ids parameter")

            # For Task Relationship fields, value should be {"add": [task_ids]}
            payload_value = {"add": property_link_ids}

            set_response = set_custom_field(
                task_regular_id,  # MUST use regular ID, not TICKET-xxxxx
                PROPERTY_LINK_FIELD_ID,
                payload_value  # {"add": ["868ckm4qz"]}
            )
            result['action_taken'] = 'propagated'
            result['success'] = True
            print(f"✅ Successfully set property_link on subtask")
            print(f"   API Response: {json.dumps(set_response, indent=2)}")

        return result

    except requests.exceptions.RequestException as e:
        result['error'] = f'API Error: {str(e)}'
        print(f"❌ API Error: {e}")
        return result
    except Exception as e:
        result['error'] = f'Error: {str(e)}'
        print(f"❌ Error: {e}")
        return result


def test_multiple_tasks(task_ids: List[str], dry_run: bool = True):
    """
    Test property_link propagation on multiple tasks.

    Args:
        task_ids: List of task IDs to test
        dry_run: If True, only report what would happen
    """
    print("="*80)
    print("PROPERTY LINK PROPAGATION TEST")
    print("="*80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will make changes)'}")
    print(f"Tasks to check: {len(task_ids)}")

    results = []

    for task_id in task_ids:
        result = propagate_property_link(task_id, dry_run=dry_run)
        results.append(result)
        print("-"*80)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    for r in results:
        print(f"\n{r['task_id']} - {r['task_name']}")
        print(f"  Action: {r['action_taken']}")
        print(f"  Success: {r['success']}")
        if r['error']:
            print(f"  Error: {r['error']}")
        if r['property_link_value']:
            print(f"  Property Link: {r['property_link_value']}")

    print("\n" + "="*80)


if __name__ == '__main__':
    # Test with the sample task (subtask missing property_link)
    test_tasks = [
        'TICKET-65711',  # The subtask from your example
        # Add more task IDs here to test
    ]

    # Run in DRY RUN mode first
    test_multiple_tasks(test_tasks, dry_run=True)

    # Uncomment below to actually make changes
    # print("\n\nRunning LIVE mode...")
    # test_multiple_tasks(test_tasks, dry_run=False)
