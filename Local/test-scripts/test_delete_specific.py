#!/usr/bin/env python3
"""
Test deleting a specific task
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

def test_delete_specific_task():
    """Test deleting the specific task provided by user"""
    
    # Task ID from the URL provided
    task_id = "868fnw12d"
    
    print("=" * 60)
    print(f"  TESTING DELETE FOR TASK: {task_id}")
    print("=" * 60)
    
    # First, let's get the task to see what we're deleting
    get_url = f"https://api.clickup.com/api/v2/task/{task_id}"
    
    headers = {
        "Authorization": CLICKUP_API_KEY
    }
    
    params = {
        "custom_task_ids": "true",
        "team_id": CLICKUP_TEAM_ID
    }
    
    print(f"\n1. Getting task details...")
    response = requests.get(get_url, headers=headers, params=params)
    
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Found task: {task.get('name', 'Unknown')}")
        print(f"   Status: {task.get('status', {}).get('status', 'Unknown')}")
        print(f"   Custom ID: {task.get('custom_id', 'None')}")
    else:
        print(f"❌ Could not get task: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return False
    
    # Now delete the task
    delete_url = f"https://api.clickup.com/api/v2/task/{task_id}"
    
    print(f"\n2. Deleting task {task_id}...")
    print("   URL: " + delete_url)
    
    response = requests.delete(delete_url, headers=headers, params=params)
    
    print(f"   Response Status: {response.status_code}")
    
    if response.status_code in [200, 204]:
        print(f"✅ Task deleted successfully!")
        
        # Try to get the task again to confirm it's deleted
        print(f"\n3. Verifying deletion...")
        verify_response = requests.get(get_url, headers=headers, params=params)
        
        if verify_response.status_code == 404:
            print(f"✅ Confirmed: Task no longer exists")
        elif verify_response.status_code == 200:
            print(f"⚠️  Warning: Task still exists (might be in trash)")
        else:
            print(f"   Verify status: {verify_response.status_code}")
        
        return True
    else:
        print(f"❌ Failed to delete task")
        print(f"   Response: {response.text[:500]}")
        return False

if __name__ == "__main__":
    if not CLICKUP_API_KEY:
        print("❌ CLICKUP_API_KEY not found in .env")
        sys.exit(1)
    
    print(f"✅ API Key loaded: {CLICKUP_API_KEY[:10]}...")
    print(f"✅ Team ID: {CLICKUP_TEAM_ID}")
    
    success = test_delete_specific_task()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DELETE endpoint works correctly!")
        print("   The task has been deleted from ClickUp")
    else:
        print("❌ DELETE endpoint test failed")
        print("   Check the error messages above")
    print("=" * 60)