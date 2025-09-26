#!/usr/bin/env python3
"""
Test using the CORRECT ClickUp API endpoint for setting custom fields
"""

import requests
from datetime import datetime

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

headers = {
    "Authorization": API_KEY,
    "Content-Type": "application/json"
}

# Test setting fields ONE AT A TIME with the correct endpoint
print(f"Testing correct API endpoint for task {TASK_ID}\n")

# 1. Set ESCALATION_REASON
field_id = "c6e0281e-9001-42d7-a265-8f5da6b71132"
print(f"Setting ESCALATION_REASON...")
response = requests.post(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
    headers=headers,
    json={"value": "TEST: This task needs urgent attention"}
)
print(f"  Status: {response.status_code}")
if not response.ok:
    print(f"  Error: {response.text}")

# 2. Set ESCALATION_AI_SUMMARY  
field_id = "e9e831f2-b439-4067-8e88-6b715f4263b2"
print(f"Setting ESCALATION_AI_SUMMARY...")
response = requests.post(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
    headers=headers,
    json={"value": "AI Analysis: Critical escalation required"}
)
print(f"  Status: {response.status_code}")
if not response.ok:
    print(f"  Error: {response.text}")

# 3. Set ESCALATION_STATUS (dropdown)
field_id = "8d784bd0-18e5-4db3-b45e-9a2900262e04"
print(f"Setting ESCALATION_STATUS to 'Escalated'...")
response = requests.post(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
    headers=headers,
    json={"value": "Escalated"}
)
print(f"  Status: {response.status_code}")
if not response.ok:
    print(f"  Error: {response.text}")

# 4. Set ESCALATION_TIMESTAMP
field_id = "5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f"
timestamp = int(datetime.now().timestamp() * 1000)
print(f"Setting ESCALATION_TIMESTAMP...")
response = requests.post(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
    headers=headers,
    json={
        "value": timestamp,
        "value_options": {"time": True}  # Include time for date field
    }
)
print(f"  Status: {response.status_code}")
if not response.ok:
    print(f"  Error: {response.text}")

# Now fetch the task to verify
print(f"\n✅ Fetching task to verify fields were set...")
get_response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": API_KEY}
)

if get_response.ok:
    task = get_response.json()
    print("\nCustom field values after update:")
    
    field_map = {
        'c6e0281e-9001-42d7-a265-8f5da6b71132': 'ESCALATION_REASON',
        'e9e831f2-b439-4067-8e88-6b715f4263b2': 'ESCALATION_AI_SUMMARY',
        '8d784bd0-18e5-4db3-b45e-9a2900262e04': 'ESCALATION_STATUS',
        '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f': 'ESCALATION_TIMESTAMP'
    }
    
    for cf in task.get('custom_fields', []):
        if cf['id'] in field_map:
            value = cf.get('value')
            if cf['type'] == 'drop_down' and value:
                # For dropdown, value might be the option name or ID
                value = value if isinstance(value, str) else 'Set (complex value)'
            elif cf['type'] == 'date' and value:
                # Convert timestamp to readable date
                from datetime import datetime
                try:
                    value = datetime.fromtimestamp(int(value)/1000).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            print(f"  {field_map[cf['id']]}: {value if value else 'NOT SET'}")
else:
    print(f"Failed to fetch task: {get_response.status_code}")