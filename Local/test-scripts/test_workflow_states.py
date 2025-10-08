#!/usr/bin/env python3
"""
Test the complete escalation workflow states
"""

import requests
from datetime import datetime

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

FIELD_IDS = {
    'ESCALATION_REASON': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
    'ESCALATION_AI_SUMMARY': 'e9e831f2-b439-4067-8e88-6b715f4263b2',
    'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
    'SUPERVISOR_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
}

def clear_all_fields():
    """Clear all escalation fields to start fresh"""
    print("🧹 Clearing all escalation fields...")
    
    fields_to_clear = [
        (FIELD_IDS['ESCALATION_REASON'], ""),
        (FIELD_IDS['ESCALATION_AI_SUMMARY'], ""),
        (FIELD_IDS['ESCALATION_STATUS'], 0),  # "Not Escalated"
        (FIELD_IDS['SUPERVISOR_RESPONSE'], ""),
    ]
    
    for field_id, value in fields_to_clear:
        response = requests.post(
            f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
            headers={
                "Authorization": API_KEY,
                "Content-Type": "application/json"
            },
            json={"value": value}
        )
        print(f"  Clear {field_id}: {response.status_code}")

def set_escalation():
    """Simulate escalation submission"""
    print("🚨 Setting escalation fields...")
    
    fields = [
        (FIELD_IDS['ESCALATION_REASON'], "WORKFLOW TEST: Task needs urgent attention"),
        (FIELD_IDS['ESCALATION_AI_SUMMARY'], "WORKFLOW TEST: AI Analysis shows critical priority"),
        (FIELD_IDS['ESCALATION_STATUS'], 1),  # "Escalated"
    ]
    
    for field_id, value in fields:
        response = requests.post(
            f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
            headers={
                "Authorization": API_KEY,
                "Content-Type": "application/json"
            },
            json={"value": value}
        )
        print(f"  Set {field_id}: {response.status_code}")

def set_supervisor_response():
    """Simulate supervisor response"""
    print("✅ Setting supervisor response...")
    
    fields = [
        (FIELD_IDS['SUPERVISOR_RESPONSE'], "WORKFLOW TEST: Supervisor has reviewed and resolved the issue"),
        (FIELD_IDS['ESCALATION_STATUS'], 2),  # "Resolved"
    ]
    
    for field_id, value in fields:
        response = requests.post(
            f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
            headers={
                "Authorization": API_KEY,
                "Content-Type": "application/json"
            },
            json={"value": value}
        )
        print(f"  Set {field_id}: {response.status_code}")

def check_state():
    """Check current state detection"""
    response = requests.get(
        f"https://api.clickup.com/api/v2/task/{TASK_ID}",
        headers={"Authorization": API_KEY}
    )
    
    if not response.ok:
        print(f"❌ Failed to fetch task: {response.status_code}")
        return
    
    task = response.json()
    
    # Extract field values
    reason = None
    summary = None
    supervisor_response = None
    status_value = None
    
    for field in task.get('custom_fields', []):
        if field['id'] == FIELD_IDS['ESCALATION_REASON']:
            reason = field.get('value')
        elif field['id'] == FIELD_IDS['ESCALATION_AI_SUMMARY']:
            summary = field.get('value')
        elif field['id'] == FIELD_IDS['SUPERVISOR_RESPONSE']:
            supervisor_response = field.get('value')
        elif field['id'] == FIELD_IDS['ESCALATION_STATUS']:
            status_value = field.get('value')
    
    # Convert status to readable
    status_text = "UNKNOWN"
    if status_value == 0:
        status_text = "NOT_ESCALATED"
    elif status_value == 1:
        status_text = "ESCALATED"
    elif status_value == 2:
        status_text = "RESOLVED"
    
    # State detection logic
    is_escalated = status_text == 'ESCALATED' or reason or summary
    is_resolved = status_text == 'RESOLVED' or supervisor_response
    is_awaiting_response = is_escalated and not is_resolved
    
    print(f"\n📊 Current State:")
    print(f"  Reason: {'✓' if reason else '✗'} ({reason[:30] + '...' if reason and len(reason) > 30 else reason})")
    print(f"  Summary: {'✓' if summary else '✗'} ({summary[:30] + '...' if summary and len(summary) > 30 else summary})")
    print(f"  Status: {status_text} (value: {status_value})")
    print(f"  Supervisor Response: {'✓' if supervisor_response else '✗'} ({supervisor_response[:30] + '...' if supervisor_response and len(supervisor_response) > 30 else supervisor_response})")
    
    print(f"\n🎯 State Detection:")
    print(f"  is_escalated: {is_escalated}")
    print(f"  is_resolved: {is_resolved}")
    print(f"  is_awaiting_response: {is_awaiting_response}")
    
    if is_resolved:
        ui_state = "RESOLVED - Show complete history with all details"
    elif is_awaiting_response:
        ui_state = "AWAITING RESPONSE - Show escalation details and AI summary, allow supervisor to respond"
    else:
        ui_state = "NORMAL - Show escalation form"
        
    print(f"  Expected UI: {ui_state}")

def test_workflow():
    """Test the complete workflow"""
    print("🔄 Testing Complete Escalation Workflow\n")
    
    # State 1: Clear everything
    clear_all_fields()
    print("\n📋 State 1: Normal (no escalation)")
    check_state()
    
    # State 2: Escalated
    print("\n" + "="*50)
    set_escalation()
    print("\n📋 State 2: Escalated (awaiting response)")
    check_state()
    
    # State 3: Resolved
    print("\n" + "="*50)
    set_supervisor_response()
    print("\n📋 State 3: Resolved (complete)")
    check_state()

if __name__ == "__main__":
    test_workflow()