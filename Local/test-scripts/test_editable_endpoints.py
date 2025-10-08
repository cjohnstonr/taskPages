#!/usr/bin/env python3
"""
Test script for wait-node-editable API endpoints
Tests both update custom field and delete task endpoints
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import time

# Load environment variables
backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{RESET}")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_info(text):
    print(f"{YELLOW}ℹ️  {text}{RESET}")

def test_update_custom_field_direct():
    """Test updating a custom field directly via ClickUp API"""
    print_header("Testing Custom Field Update (Direct ClickUp API)")
    
    # Test task and field IDs
    task_id = "868fkbnta"  # A test task ID
    field_id = FIELD_IDS['MCP_ACTION']  # MCP_Action field
    new_value = f"TEST_ACTION_{int(time.time())}"
    
    print_info(f"Task ID: {task_id}")
    print_info(f"Field ID: {field_id}")
    print_info(f"New Value: {new_value}")
    
    # Make the API call
    url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {
        "custom_task_ids": "true",
        "team_id": CLICKUP_TEAM_ID
    }
    
    payload = {
        "value": new_value
    }
    
    try:
        print_info("Making API call...")
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print_success("Field updated successfully!")
            print(f"Response: {json.dumps(response.json(), indent=2)[:500]}")
            return True
        else:
            print_error(f"Failed to update field: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_checkbox_field_update():
    """Test updating the Executed checkbox field"""
    print_header("Testing Checkbox Field Update (Executed)")
    
    task_id = "868fkbnta"
    field_id = FIELD_IDS['EXECUTED']
    
    print_info(f"Task ID: {task_id}")
    print_info(f"Field ID: {field_id}")
    print_info("Setting Executed to: true")
    
    url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{field_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {
        "custom_task_ids": "true",
        "team_id": CLICKUP_TEAM_ID
    }
    
    # For checkbox, the value should be boolean
    payload = {
        "value": True
    }
    
    try:
        print_info("Making API call...")
        response = requests.post(url, headers=headers, params=params, json=payload)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print_success("Checkbox updated successfully!")
            return True
        else:
            print_error(f"Failed to update checkbox: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def test_delete_task():
    """Test deleting a task - BE CAREFUL WITH THIS"""
    print_header("Testing Task Deletion (CAUTION!)")
    
    # Create a test task first to delete
    print_info("First, let's create a test task to delete...")
    
    # Create test task
    create_url = "https://api.clickup.com/api/v2/list/901103436094/task"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    create_payload = {
        "name": "TEST_TASK_TO_DELETE",
        "description": "This task will be deleted by test script"
    }
    
    try:
        response = requests.post(create_url, headers=headers, json=create_payload)
        
        if response.status_code != 200:
            print_error("Failed to create test task")
            return False
            
        task_data = response.json()
        task_id = task_data['id']
        print_success(f"Created test task: {task_id}")
        
        # Wait a moment
        time.sleep(2)
        
        # Now delete it
        print_info(f"Deleting task: {task_id}")
        delete_url = f"https://api.clickup.com/api/v2/task/{task_id}"
        
        params = {
            "custom_task_ids": "true",
            "team_id": CLICKUP_TEAM_ID
        }
        
        response = requests.delete(delete_url, headers=headers, params=params)
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code in [200, 204]:
            print_success("Task deleted successfully!")
            return True
        else:
            print_error(f"Failed to delete task: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

def get_task_custom_fields(task_id):
    """Helper to get current custom field values"""
    print_header(f"Getting Current Field Values for Task {task_id}")
    
    url = f"https://api.clickup.com/api/v2/task/{task_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY
    }
    
    params = {
        "custom_task_ids": "true",
        "team_id": CLICKUP_TEAM_ID
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            task = response.json()
            print_success(f"Task: {task['name']}")
            
            # Find our test fields
            for field in task.get('custom_fields', []):
                if field['id'] in [FIELD_IDS['MCP_ACTION'], FIELD_IDS['MCP_CLIENT'], FIELD_IDS['PROCESS_TEXT']]:
                    value = field.get('value', 'null')
                    print_info(f"{field['name']}: {value}")
                    
            return True
        else:
            print_error(f"Failed to get task: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Exception: {e}")
        return False

# Field IDs from our code
FIELD_IDS = {
    'EXECUTED': '13d4d660-432d-4033-9805-2ffc7d793c92',
    'MCP_ACTION': 'b5b74b80-df0a-4417-80f8-f95fd69fdf3b',
    'MCP_CLIENT': '6cbb8b35-fe7c-434d-a0cf-ae7498a2e55e',
    'PROCESS_TEXT': 'b2587292-c1bc-4ee0-8dcb-a69db68d5fe8',
    'PROCESS_STATUS': '079ab4a6-747a-4a66-960d-5df7f64b30da'
}

def main():
    print_header("ClickUp API Endpoint Test Suite")
    
    if not CLICKUP_API_KEY:
        print_error("CLICKUP_API_KEY not found in .env")
        return
    
    print_success(f"API Key loaded: {CLICKUP_API_KEY[:10]}...")
    print_success(f"Team ID: {CLICKUP_TEAM_ID}")
    
    # Menu
    print("\nSelect test to run:")
    print("1. Test updating text field (MCP_Action)")
    print("2. Test updating checkbox (Executed)")
    print("3. Test deleting a task (creates test task first)")
    print("4. Get current field values for a task")
    print("5. Run all tests")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == '1':
        test_update_custom_field_direct()
    elif choice == '2':
        test_checkbox_field_update()
    elif choice == '3':
        confirm = input("⚠️  This will create and delete a test task. Continue? (y/n): ")
        if confirm.lower() == 'y':
            test_delete_task()
    elif choice == '4':
        task_id = input("Enter task ID (or press Enter for default '868fkbnta'): ").strip()
        if not task_id:
            task_id = '868fkbnta'
        get_task_custom_fields(task_id)
    elif choice == '5':
        test_update_custom_field_direct()
        time.sleep(2)
        test_checkbox_field_update()
        time.sleep(2)
        confirm = input("⚠️  Run delete test? (y/n): ")
        if confirm.lower() == 'y':
            test_delete_task()
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()