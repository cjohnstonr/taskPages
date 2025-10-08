#!/usr/bin/env python3
"""
Automated test script for wait-node-editable API endpoints
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

# Field IDs from our code
FIELD_IDS = {
    'EXECUTED': '13d4d660-432d-4033-9805-2ffc7d793c92',
    'MCP_ACTION': 'b5b74b80-df0a-4417-80f8-f95fd69fdf3b',
    'MCP_CLIENT': '6cbb8b35-fe7c-434d-a0cf-ae7498a2e55e',
    'PROCESS_TEXT': 'b2587292-c1bc-4ee0-8dcb-a69db68d5fe8',
    'PROCESS_STATUS': '079ab4a6-747a-4a66-960d-5df7f64b30da'
}

# Test task ID - using a Process Library task we know exists
TEST_TASK_ID = "868fkbnta"

def test_get_task():
    """First, verify we can get the task"""
    print("\n1. Testing GET task...")
    
    url = f"https://api.clickup.com/api/v2/task/{TEST_TASK_ID}"
    
    headers = {"Authorization": CLICKUP_API_KEY}
    params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Task found: {task['name']}")
        print(f"   ID: {task['id']}")
        
        # Find MCP_ACTION field current value
        for field in task.get('custom_fields', []):
            if field['id'] == FIELD_IDS['MCP_ACTION']:
                print(f"   Current MCP_Action: {field.get('value', 'null')}")
                return task
    else:
        print(f"❌ Failed to get task: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    
    return None

def test_update_text_field():
    """Test updating a text custom field"""
    print("\n2. Testing UPDATE text field (MCP_Action)...")
    
    field_id = FIELD_IDS['MCP_ACTION']
    new_value = f"TEST_{int(time.time())}"
    
    url = f"https://api.clickup.com/api/v2/task/{TEST_TASK_ID}/field/{field_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
    
    payload = {"value": new_value}
    
    print(f"   Setting MCP_Action to: {new_value}")
    response = requests.post(url, headers=headers, params=params, json=payload)
    
    if response.status_code == 200:
        print(f"✅ Field updated successfully!")
        return True
    else:
        print(f"❌ Failed to update: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_update_checkbox():
    """Test updating the Executed checkbox"""
    print("\n3. Testing UPDATE checkbox (Executed)...")
    
    field_id = FIELD_IDS['EXECUTED']
    
    url = f"https://api.clickup.com/api/v2/task/{TEST_TASK_ID}/field/{field_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
    
    # Try setting to true
    payload = {"value": True}
    
    print(f"   Setting Executed to: true")
    response = requests.post(url, headers=headers, params=params, json=payload)
    
    if response.status_code == 200:
        print(f"✅ Checkbox updated successfully!")
        return True
    else:
        print(f"❌ Failed to update: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def test_create_and_delete():
    """Test creating and deleting a task"""
    print("\n4. Testing CREATE and DELETE task...")
    
    # Find a list to create task in - using a known list ID
    list_id = "901103436094"  # You may need to update this
    
    # Create a test task
    create_url = f"https://api.clickup.com/api/v2/list/{list_id}/task"
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "name": f"TEST_DELETE_{int(time.time())}",
        "description": "Test task for deletion"
    }
    
    print("   Creating test task...")
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code != 200:
        print(f"❌ Failed to create task: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False
    
    task = response.json()
    task_id = task['id']
    print(f"✅ Created task: {task_id}")
    
    # Wait a moment
    time.sleep(2)
    
    # Delete the task
    delete_url = f"https://api.clickup.com/api/v2/task/{task_id}"
    params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
    
    print(f"   Deleting task: {task_id}")
    response = requests.delete(delete_url, headers=headers, params=params)
    
    if response.status_code in [200, 204]:
        print(f"✅ Task deleted successfully!")
        return True
    else:
        print(f"❌ Failed to delete: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False

def verify_update():
    """Verify the field was actually updated"""
    print("\n5. Verifying field update...")
    
    url = f"https://api.clickup.com/api/v2/task/{TEST_TASK_ID}"
    
    headers = {"Authorization": CLICKUP_API_KEY}
    params = {"custom_task_ids": "true", "team_id": CLICKUP_TEAM_ID}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        task = response.json()
        
        # Check MCP_ACTION field
        for field in task.get('custom_fields', []):
            if field['id'] == FIELD_IDS['MCP_ACTION']:
                value = field.get('value', 'null')
                if value and value.startswith('TEST_'):
                    print(f"✅ Verified MCP_Action: {value}")
                    return True
                else:
                    print(f"⚠️  MCP_Action value: {value}")
        
        print("⚠️  Field not found or not updated")
    else:
        print(f"❌ Failed to verify: {response.status_code}")
    
    return False

def main():
    print("=" * 60)
    print("  CLICKUP API ENDPOINT TESTS")
    print("=" * 60)
    
    if not CLICKUP_API_KEY:
        print("❌ CLICKUP_API_KEY not found in .env")
        return
    
    print(f"✅ API Key: {CLICKUP_API_KEY[:10]}...")
    print(f"✅ Team ID: {CLICKUP_TEAM_ID}")
    print(f"📋 Test Task ID: {TEST_TASK_ID}")
    
    # Run tests
    results = []
    
    # Test 1: Get task
    task = test_get_task()
    results.append(("GET task", task is not None))
    
    if task:
        # Test 2: Update text field
        success = test_update_text_field()
        results.append(("UPDATE text field", success))
        
        # Test 3: Update checkbox
        success = test_update_checkbox()
        results.append(("UPDATE checkbox", success))
        
        # Test 4: Verify update
        success = verify_update()
        results.append(("VERIFY update", success))
    
    # Test 5: Create and delete
    success = test_create_and_delete()
    results.append(("CREATE & DELETE", success))
    
    # Summary
    print("\n" + "=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! The endpoints are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()