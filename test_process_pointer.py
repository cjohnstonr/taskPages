#!/usr/bin/env python3
"""
Test script to examine the Process Pointer custom field structure
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')

# The Process Pointer custom field ID
PROCESS_POINTER_FIELD_ID = '56d8c645-1e50-421c-bb62-1e3ef1cff80f'

# The task ID that has this field
TASK_ID = '868fkbmkj'

def get_task_with_process_pointer(task_id):
    """Get task details and examine the Process Pointer field structure"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found in backend/.env")
        return None
    
    print(f"🔍 Fetching task: {task_id}")
    print(f"👥 Team ID: {CLICKUP_TEAM_ID}")
    print("=" * 60)
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get task with custom fields
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    params = {
        "team_id": CLICKUP_TEAM_ID,
        "custom_task_ids": "true"
    }
    
    try:
        print(f"📡 Calling: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            task_data = response.json()
            
            print("✅ Task fetched successfully!")
            print(f"Task Name: {task_data.get('name')}")
            print(f"Task ID: {task_data.get('id')}")
            print(f"Custom ID: {task_data.get('custom_id')}")
            print("=" * 60)
            
            # Find and examine the Process Pointer field
            print("🔍 Looking for Process Pointer field...")
            custom_fields = task_data.get('custom_fields', [])
            
            process_pointer_field = None
            for field in custom_fields:
                if field.get('id') == PROCESS_POINTER_FIELD_ID:
                    process_pointer_field = field
                    break
            
            if process_pointer_field:
                print("✅ FOUND Process Pointer field!")
                print("\n📋 Field Structure:")
                print(json.dumps(process_pointer_field, indent=2))
                
                # Extract the linked task info
                print("\n🔗 Linked Task Information:")
                
                # Task relationship fields typically have 'value' as a dict with task info
                value = process_pointer_field.get('value')
                if value:
                    if isinstance(value, dict):
                        print(f"  - Linked Task ID: {value.get('id')}")
                        print(f"  - Linked Task Name: {value.get('name')}")
                        print(f"  - Linked Task Custom ID: {value.get('custom_id')}")
                        print(f"  - Linked Task Status: {value.get('status', {}).get('status')}")
                    elif isinstance(value, list) and len(value) > 0:
                        # Sometimes it's a list of tasks
                        for idx, task in enumerate(value):
                            print(f"\n  Task {idx + 1}:")
                            print(f"    - ID: {task.get('id')}")
                            print(f"    - Name: {task.get('name')}")
                            print(f"    - Custom ID: {task.get('custom_id')}")
                    elif isinstance(value, str):
                        # Sometimes it's just a task ID string
                        print(f"  - Linked Task ID: {value}")
                else:
                    print("  - No linked task (field is empty)")
                
                # Check field metadata
                print("\n📊 Field Metadata:")
                print(f"  - Field Name: {process_pointer_field.get('name')}")
                print(f"  - Field Type: {process_pointer_field.get('type')}")
                print(f"  - Required: {process_pointer_field.get('required', False)}")
                
            else:
                print(f"⚠️ Process Pointer field ({PROCESS_POINTER_FIELD_ID}) not found in task")
                print("\n📋 Available custom fields:")
                for field in custom_fields:
                    print(f"  - {field.get('name')}: {field.get('id')}")
            
            # Save full response for analysis
            with open('process_pointer_response.json', 'w') as f:
                json.dump(task_data, f, indent=2)
            print(f"\n💾 Full task data saved to process_pointer_response.json")
            
            return task_data
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")
    
    return None

if __name__ == "__main__":
    print("🚀 ClickUp Process Pointer Field Analyzer")
    print("=" * 60)
    
    task_data = get_task_with_process_pointer(TASK_ID)
    
    if task_data:
        print("\n✅ Analysis complete!")
        print("\n🎯 UI Integration Plan:")
        print("1. Extract Process Pointer field from mainTask.custom_fields")
        print("2. If field has value, display linked task name and ID")
        print("3. Create clickable link to open in ClickUp")
        print("4. Add small section below Process Library Task section")