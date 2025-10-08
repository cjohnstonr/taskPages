#!/usr/bin/env python3
"""
Check what custom fields are actually available on a task
"""

import os
import requests
import json

TASK_ID = "868fkbrfv"
CLICKUP_API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

# Get the task details
print(f"Fetching task {TASK_ID}...")
response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": CLICKUP_API_KEY}
)

if response.ok:
    task = response.json()
    print(f"Task: {task.get('name', 'Unknown')}")
    print(f"List ID: {task.get('list', {}).get('id', 'Unknown')}")
    print(f"Space ID: {task.get('space', {}).get('id', 'Unknown')}")
    
    print("\nCustom fields available on this task:")
    if 'custom_fields' in task:
        for cf in task['custom_fields']:
            print(f"  - ID: {cf['id']}")
            print(f"    Name: {cf['name']}")
            print(f"    Type: {cf['type']}")
            print(f"    Value: {cf.get('value', 'NOT SET')}")
            print()
    else:
        print("  No custom fields found!")
        
    # Now get the list to see what fields are defined
    list_id = task.get('list', {}).get('id')
    if list_id:
        print(f"\nFetching list {list_id} to see field definitions...")
        list_response = requests.get(
            f"https://api.clickup.com/api/v2/list/{list_id}",
            headers={"Authorization": CLICKUP_API_KEY}
        )
        
        if list_response.ok:
            list_data = list_response.json()
            print(f"List: {list_data.get('name', 'Unknown')}")
            
            # Check for custom fields at different levels
            for level in ['custom_fields', 'space', 'folder']:
                if level in list_data:
                    if level == 'custom_fields':
                        fields = list_data[level]
                    else:
                        fields = list_data[level].get('custom_fields', [])
                    
                    if fields:
                        print(f"\nCustom fields from {level}:")
                        for cf in fields:
                            print(f"  - {cf['name']} (ID: {cf['id']})")
else:
    print(f"Failed to fetch task: {response.status_code}")
    print(response.text)