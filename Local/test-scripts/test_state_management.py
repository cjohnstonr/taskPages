#!/usr/bin/env python3
"""
Test the state management fixes by checking field values and state detection logic
"""

import requests

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

# UUID mapping for testing
ESCALATION_STATUS_VALUES = {
    'ESCALATED': '8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497',
    'RESOLVED': 'cbf82936-5488-4612-93a7-f8161071b0eb'
}

FIELD_IDS = {
    'ESCALATION_REASON': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
    'ESCALATION_AI_SUMMARY': 'e9e831f2-b439-4067-8e88-6b715f4263b2',
    'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
    'ESCALATED_TO': '934811f1-239f-4d53-880c-3655571fd02e',
    'ESCALATION_TIMESTAMP': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
    'SUPERVISOR_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
    'ESCALATION_RESOLVED_TIMESTAMP': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
}

def get_escalation_status(task):
    """Simulate the frontend function"""
    if not task.get('custom_fields'):
        return None
    
    for field in task['custom_fields']:
        if field['id'] == FIELD_IDS['ESCALATION_STATUS']:
            value = field.get('value')
            # ClickUp stores dropdown values as orderindex integers
            # 0="Not Escalated", 1="Escalated", 2="Resolved"
            if value == 0:
                return 'NOT_ESCALATED'
            elif value == 1:
                return 'ESCALATED'
            elif value == 2:
                return 'RESOLVED'
            # Fallback for UUID values
            elif value == ESCALATION_STATUS_VALUES['ESCALATED']:
                return 'ESCALATED'
            elif value == ESCALATION_STATUS_VALUES['RESOLVED']:
                return 'RESOLVED'
    return None

def get_custom_field(task, field_id):
    """Simulate the frontend function"""
    if not task.get('custom_fields'):
        return None
    
    for field in task['custom_fields']:
        if field['id'] == field_id:
            return field.get('value')
    return None

def test_state_detection():
    """Test state detection logic"""
    print(f"Testing state detection for task {TASK_ID}")
    
    # Fetch current task
    response = requests.get(
        f"https://api.clickup.com/api/v2/task/{TASK_ID}",
        headers={"Authorization": API_KEY}
    )
    
    if not response.ok:
        print(f"❌ Failed to fetch task: {response.status_code}")
        return
    
    task = response.json()
    
    # Test field extraction
    reason = get_custom_field(task, FIELD_IDS['ESCALATION_REASON'])
    summary = get_custom_field(task, FIELD_IDS['ESCALATION_AI_SUMMARY'])
    supervisor_response = get_custom_field(task, FIELD_IDS['SUPERVISOR_RESPONSE'])
    escalation_status = get_escalation_status(task)
    
    print(f"\n📋 Current Field Values:")
    print(f"  Reason: {reason}")
    print(f"  Summary: {summary}")
    print(f"  Status UUID: {get_custom_field(task, FIELD_IDS['ESCALATION_STATUS'])}")
    print(f"  Status Readable: {escalation_status}")
    print(f"  Supervisor Response: {supervisor_response}")
    
    # Test state logic
    is_escalated = escalation_status == 'ESCALATED' or reason or summary
    is_resolved = escalation_status == 'RESOLVED' or supervisor_response
    is_awaiting_response = is_escalated and not is_resolved
    
    print(f"\n🔍 State Detection Results:")
    print(f"  Is Escalated: {is_escalated}")
    print(f"  Is Resolved: {is_resolved}")
    print(f"  Is Awaiting Response: {is_awaiting_response}")
    
    # Determine what UI state should show
    if is_resolved:
        ui_state = "RESOLVED STATE - Show complete history"
    elif is_awaiting_response:
        ui_state = "AWAITING RESPONSE STATE - Show AI summary, allow supervisor response"
    else:
        ui_state = "NORMAL STATE - Show escalation form"
    
    print(f"\n🎯 Expected UI State: {ui_state}")
    
    return {
        'escalated': is_escalated,
        'resolved': is_resolved,
        'awaiting': is_awaiting_response,
        'ui_state': ui_state
    }

if __name__ == "__main__":
    test_state_detection()