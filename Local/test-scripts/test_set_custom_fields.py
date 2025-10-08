#!/usr/bin/env python3
"""
Test script to manually set all 7 custom fields on a ClickUp task
to verify the field IDs are correct and working
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Task ID to test with
TASK_ID = "868fkbrfv"

# ClickUp API configuration
CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
if not CLICKUP_API_KEY:
    print("ERROR: CLICKUP_API_KEY not found in environment")
    exit(1)

# Custom field IDs from the frontend
FIELD_IDS = {
    'ESCALATION_REASON': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
    'ESCALATION_AI_SUMMARY': 'e9e831f2-b439-4067-8e88-6b715f4263b2',
    'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
    'ESCALATED_TO': '934811f1-239f-4d53-880c-3655571fd02e',
    'ESCALATION_TIMESTAMP': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
    'SUPERVISOR_RESPONSE': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
    'ESCALATION_RESOLVED_TIMESTAMP': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a'
}

def set_custom_fields():
    """Set all 7 custom fields on the test task"""
    
    # Prepare test values for all fields
    current_timestamp = int(datetime.now().timestamp() * 1000)
    
    custom_fields = [
        {"id": FIELD_IDS['ESCALATION_REASON'], "value": "TEST: This is a test escalation reason"},
        {"id": FIELD_IDS['ESCALATION_AI_SUMMARY'], "value": "TEST: AI Summary - This task needs attention"},
        {"id": FIELD_IDS['ESCALATION_STATUS'], "value": "pending"},
        {"id": FIELD_IDS['ESCALATED_TO'], "value": "test@example.com"},
        {"id": FIELD_IDS['ESCALATION_TIMESTAMP'], "value": current_timestamp},
        {"id": FIELD_IDS['SUPERVISOR_RESPONSE'], "value": "TEST: Supervisor response here"},
        {"id": FIELD_IDS['ESCALATION_RESOLVED_TIMESTAMP'], "value": current_timestamp}
    ]
    
    print(f"Setting custom fields on task: {TASK_ID}")
    print(f"Fields being set:")
    for field in custom_fields:
        field_name = [k for k, v in FIELD_IDS.items() if v == field['id']][0]
        print(f"  - {field_name}: {field['value']}")
    
    # Make API call to update task
    url = f"https://api.clickup.com/api/v2/task/{TASK_ID}"
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "custom_fields": custom_fields
    }
    
    print(f"\nSending request to: {url}")
    response = requests.put(url, headers=headers, json=payload)
    
    print(f"Response status: {response.status_code}")
    
    if response.ok:
        print("✅ SUCCESS: Custom fields set successfully!")
        
        # Now fetch the task to verify fields were actually set
        print("\nFetching task to verify fields...")
        get_response = requests.get(
            f"https://api.clickup.com/api/v2/task/{TASK_ID}",
            headers={"Authorization": CLICKUP_API_KEY}
        )
        
        if get_response.ok:
            task = get_response.json()
            print("\nCustom fields on task after update:")
            if 'custom_fields' in task:
                for cf in task['custom_fields']:
                    if cf['id'] in FIELD_IDS.values():
                        field_name = [k for k, v in FIELD_IDS.items() if v == cf['id']][0]
                        print(f"  - {field_name}: {cf.get('value', 'NOT SET')}")
            else:
                print("  No custom fields found!")
        else:
            print(f"❌ Failed to fetch task: {get_response.status_code}")
            print(get_response.text)
    else:
        print(f"❌ FAILED: {response.status_code}")
        print(response.text)
        
        # Try to parse error
        try:
            error_data = response.json()
            if 'err' in error_data:
                print(f"\nError message: {error_data['err']}")
                
            # Check if it's a custom field error
            if 'FIELD' in response.text.upper():
                print("\n⚠️  This appears to be a custom field error!")
                print("The field IDs might be incorrect or the fields don't exist on this task's list.")
        except:
            pass

if __name__ == "__main__":
    set_custom_fields()