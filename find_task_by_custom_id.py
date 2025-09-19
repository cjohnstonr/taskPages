#!/usr/bin/env python3
"""
Find actual task ID by custom ID
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')

def find_task_by_custom_id(custom_id):
    """Search for a task by custom ID"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found")
        return None
    
    print(f"🔍 Searching for task with custom ID: {custom_id}")
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Search using ClickUp's search endpoint
    url = f"https://api.clickup.com/api/v2/team/{CLICKUP_TEAM_ID}/task"
    params = {
        "custom_task_ids": "true",
        "include_closed": "true",
        "subtasks": "true"
    }
    
    # Try searching with custom fields
    search_url = f"https://api.clickup.com/api/v2/task/{custom_id}"
    
    try:
        # First try direct access with custom ID
        response = requests.get(search_url, headers=headers, params={"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}, timeout=10)
        
        if response.status_code == 200:
            task = response.json()
            print(f"✅ Found task!")
            print(f"   Actual ID: {task.get('id')}")
            print(f"   Name: {task.get('name')}")
            print(f"   Custom ID: {task.get('custom_id')}")
            
            # Now check for Process Pointer field
            custom_fields = task.get('custom_fields', [])
            for field in custom_fields:
                if field.get('id') == '56d8c645-1e50-421c-bb62-1e3ef1cff80f':
                    print("\n🎯 PROCESS POINTER FIELD FOUND!")
                    print(f"Field structure: {json.dumps(field, indent=2)}")
                    
                    if field.get('value'):
                        print("\n📎 Related Tasks in Process Pointer:")
                        for related_task in field.get('value', []):
                            print(f"  - {related_task.get('name')} (ID: {related_task.get('id')})")
                    break
            
            return task.get('id')
        else:
            print(f"❌ Could not find task: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")
    
    return None

if __name__ == "__main__":
    import sys
    custom_id = sys.argv[1] if len(sys.argv) > 1 else "TICKET-47573"
    
    actual_id = find_task_by_custom_id(custom_id)
    
    if actual_id:
        print(f"\n💡 Use this ID for testing: {actual_id}")
        
        # Now test with the actual ID
        print("\n" + "="*60)
        print("Testing with actual ID...")
        import subprocess
        result = subprocess.run(['python', 'test_relationship_field.py', actual_id], capture_output=True, text=True)
        print(result.stdout)