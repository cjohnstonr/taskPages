#!/usr/bin/env python3
"""
Test script to fetch a task and examine relationship custom fields
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

# The relationship field ID you provided
RELATIONSHIP_FIELD_ID = '56d8c645-1e50-421c-bb62-1e3ef1cff80f'

def get_task_with_custom_fields(task_id):
    """Fetch a task and examine its custom fields"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found in backend/.env")
        return None
    
    print(f"🔍 Fetching task: {task_id}")
    print("=" * 60)
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get task with custom fields
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    params = {
        "include_subtasks": "true",
        "include_closed": "true"
    }
    
    try:
        print(f"📡 API Call: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            task = response.json()
            
            print(f"✅ Task Name: {task.get('name')}")
            print(f"📋 Task ID: {task.get('id')}")
            print(f"🏷️  Custom ID: {task.get('custom_id')}")
            print("=" * 60)
            
            # Check custom fields
            custom_fields = task.get('custom_fields', [])
            print(f"📊 Total Custom Fields: {len(custom_fields)}")
            print("=" * 60)
            
            # Look for relationship fields
            relationship_fields = []
            for field in custom_fields:
                # Check if this might be a relationship field
                if field.get('type') in ['tasks', 'task', 'relationship'] or \
                   isinstance(field.get('value'), list) and field.get('value') and \
                   isinstance(field.get('value')[0], dict) and 'task_id' in field.get('value', [{}])[0]:
                    relationship_fields.append(field)
                
                # Also check for our specific field ID
                if field.get('id') == RELATIONSHIP_FIELD_ID:
                    print("🎯 FOUND THE RELATIONSHIP FIELD!")
                    print(f"Field structure: {json.dumps(field, indent=2)}")
            
            # Display all relationship-type fields found
            if relationship_fields:
                print("\n🔗 RELATIONSHIP FIELDS FOUND:")
                for rf in relationship_fields:
                    print(f"\nField Name: {rf.get('name')}")
                    print(f"Field ID: {rf.get('id')}")
                    print(f"Field Type: {rf.get('type')}")
                    print(f"Value Type: {type(rf.get('value'))}")
                    
                    # Show the value structure
                    value = rf.get('value')
                    if isinstance(value, list) and value:
                        print(f"Number of related tasks: {len(value)}")
                        print("First related task structure:")
                        print(json.dumps(value[0], indent=2))
                    elif value:
                        print(f"Value structure: {json.dumps(value, indent=2)}")
                    else:
                        print("Value: Empty/None")
            else:
                print("\n⚠️  No relationship fields found in this task")
            
            # Show sample of all custom fields for analysis
            print("\n📋 ALL CUSTOM FIELDS (first 5):")
            for i, field in enumerate(custom_fields[:5]):
                print(f"\n{i+1}. Field: {field.get('name')}")
                print(f"   ID: {field.get('id')}")
                print(f"   Type: {field.get('type')}")
                value = field.get('value')
                if isinstance(value, list):
                    print(f"   Value: [Array with {len(value)} items]")
                    if value and isinstance(value[0], dict):
                        print(f"   First item keys: {list(value[0].keys())}")
                elif isinstance(value, dict):
                    print(f"   Value keys: {list(value.keys())}")
                else:
                    print(f"   Value: {value}")
            
            return task
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")
    
    return None

def test_multiple_tasks():
    """Test multiple tasks to find ones with relationship fields"""
    
    # Test task IDs - using ones from your screenshots
    test_tasks = [
        'TICKET-66254',  # From your screenshot
        '868fkbmkj',     # From previous tests
        '868fkbrfv',     # From previous tests
    ]
    
    for task_id in test_tasks:
        print("\n" + "🔍" * 30)
        print(f"TESTING TASK: {task_id}")
        print("🔍" * 30 + "\n")
        
        get_task_with_custom_fields(task_id)
        print("\n")

if __name__ == "__main__":
    print("🚀 ClickUp Task Relationship Field Test")
    print("=" * 60)
    
    # Test specific task if provided as argument
    if len(sys.argv) > 1:
        task_id = sys.argv[1]
        print(f"Testing specific task: {task_id}")
        get_task_with_custom_fields(task_id)
    else:
        # Test multiple tasks
        test_multiple_tasks()