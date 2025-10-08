#!/usr/bin/env python3
"""
Debug the ESCALATION_STATUS field to see what values are actually stored
"""

import requests

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": API_KEY}
)

if response.ok:
    task = response.json()
    print("🔍 All custom fields:")
    
    for field in task.get('custom_fields', []):
        if field['id'] == '8d784bd0-18e5-4db3-b45e-9a2900262e04':  # ESCALATION_STATUS
            print(f"\n📋 ESCALATION_STATUS Field Details:")
            print(f"  ID: {field.get('id')}")
            print(f"  Name: {field.get('name')}")
            print(f"  Type: {field.get('type')}")
            print(f"  Value: {field.get('value')} (type: {type(field.get('value'))})")
            print(f"  Raw field: {field}")
            
            # Check type config for dropdown options
            if 'type_config' in field:
                print(f"\n  Dropdown Options:")
                for option in field.get('type_config', {}).get('options', []):
                    print(f"    - '{option['name']}' -> UUID: '{option['id']}'")
    
    print(f"\n🔧 Setting status to 'Escalated' UUID...")
    # Try setting with the correct UUID
    set_response = requests.post(
        f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/8d784bd0-18e5-4db3-b45e-9a2900262e04",
        headers={
            "Authorization": API_KEY,
            "Content-Type": "application/json"
        },
        json={"value": "8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497"}  # UUID for 'Escalated'
    )
    
    print(f"Set status response: {set_response.status_code}")
    if not set_response.ok:
        print(f"Error: {set_response.text}")
    
    # Check again
    verify_response = requests.get(
        f"https://api.clickup.com/api/v2/task/{TASK_ID}",
        headers={"Authorization": API_KEY}
    )
    
    if verify_response.ok:
        verify_task = verify_response.json()
        for field in verify_task.get('custom_fields', []):
            if field['id'] == '8d784bd0-18e5-4db3-b45e-9a2900262e04':
                print(f"\n✅ After setting - Value: {field.get('value')} (type: {type(field.get('value'))})")