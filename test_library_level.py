#!/usr/bin/env python3
"""
Test to check library level of subtasks
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')

LIBRARY_LEVEL_FIELD_ID = 'e49ccff6-f042-4e47-b452-0812ba128cfb'

def get_task_and_subtasks(task_id):
    """Get task and its subtasks to check library level"""
    
    # Get the main task with subtasks
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    headers = {"Authorization": CLICKUP_API_KEY}
    params = {
        "custom_task_ids": "true",
        "team_id": CLICKUP_TEAM_ID,
        "include_subtasks": "true"
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        task = response.json()
        print(f"Main Task: {task['name']}")
        print(f"Custom Item ID: {task.get('custom_item_id', 'None')}")
        
        # Check subtasks
        subtasks = task.get('subtasks', [])
        print(f"\nFound {len(subtasks)} subtasks")
        
        # Get details for each subtask
        for subtask_ref in subtasks[:5]:  # Check first 5
            print(f"\n{'='*50}")
            print(f"Fetching subtask: {subtask_ref['id']}")
            
            # Get full subtask details
            subtask_url = f"https://api.clickup.com/api/v2/task/{subtask_ref['id']}"
            subtask_response = requests.get(subtask_url, headers=headers, params=params)
            
            if subtask_response.status_code == 200:
                subtask = subtask_response.json()
                print(f"Name: {subtask['name']}")
                print(f"ID: {subtask['id']}")
                print(f"Custom ID: {subtask.get('custom_id', 'None')}")
                
                # Find library level field
                library_level_found = False
                for field in subtask.get('custom_fields', []):
                    if field['id'] == LIBRARY_LEVEL_FIELD_ID:
                        library_level_found = True
                        print(f"\n📌 LIBRARY_LEVEL field found:")
                        print(f"   Value: {field.get('value')}")
                        print(f"   Type Config: {json.dumps(field.get('type_config', {}), indent=2)}")
                        
                        # Try to find the actual name
                        options = field.get('type_config', {}).get('options', [])
                        if options and field.get('value') is not None:
                            selected_option = next((opt for opt in options if opt.get('orderindex') == field['value']), None)
                            if selected_option:
                                print(f"   Selected Option Name: {selected_option.get('name')}")
                                print(f"   Is it 'Wait'?: {selected_option.get('name') == 'Wait'}")
                        break
                
                if not library_level_found:
                    print("   ⚠️  LIBRARY_LEVEL field NOT found in custom_fields")
                    print("   Available field IDs:")
                    for field in subtask.get('custom_fields', []):
                        print(f"      - {field['id']}: {field['name']}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    # Test with a Process Library task
    test_task_id = "868fkbmkj"  # Process Library task
    
    print("=" * 60)
    print("LIBRARY LEVEL FIELD CHECK")
    print("=" * 60)
    print(f"Testing task: {test_task_id}")
    print(f"Library Level Field ID: {LIBRARY_LEVEL_FIELD_ID}")
    print()
    
    get_task_and_subtasks(test_task_id)