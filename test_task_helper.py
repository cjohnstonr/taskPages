#!/usr/bin/env python3
"""
Test script to debug task-helper initialization issue
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('backend/.env')

BACKEND_URL = "https://taskpages-backend.onrender.com"
TASK_ID = "868fqc8ja"
CLICKUP_TOKEN = os.getenv('CLICKUP_API_KEY')

print("Testing Task Helper Initialization Issue\n")
print("=" * 50)

# Test 1: Check if task exists in ClickUp
print("\n1. Testing ClickUp API directly:")
print(f"   Task ID: {TASK_ID}")

clickup_response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": CLICKUP_TOKEN}
)

if clickup_response.ok:
    task_data = clickup_response.json()
    print(f"   ✅ Task found: {task_data.get('name', 'Unknown')}")
    print(f"   Status: {task_data.get('status', {}).get('status', 'Unknown')}")
else:
    print(f"   ❌ ClickUp API error: {clickup_response.status_code}")
    print(f"   Response: {clickup_response.text}")

# Test 2: Check what endpoints exist on backend
print("\n2. Testing Backend Endpoints:")

# This endpoint DOES NOT EXIST (causing the 404)
wrong_endpoint = f"{BACKEND_URL}/api/initialize/{TASK_ID}"
print(f"\n   Testing (wrong): {wrong_endpoint}")
try:
    response = requests.get(wrong_endpoint)
    print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# This endpoint EXISTS for wait-node
correct_endpoint = f"{BACKEND_URL}/api/wait-node/initialize/{TASK_ID}"
print(f"\n   Testing (wait-node): {correct_endpoint}")
try:
    response = requests.get(correct_endpoint)
    print(f"   Status: {response.status_code}")
    if response.status_code == 401:
        print("   Note: 401 means endpoint exists but needs authentication")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: What the task-helper should be calling
print("\n3. Solution:")
print("   The task-helper frontend is calling:")
print(f"   ❌ /api/initialize/{TASK_ID}")
print("\n   But it should be calling either:")
print(f"   ✅ /api/wait-node/initialize/{TASK_ID}")
print("   OR we need to create:")
print(f"   ✅ /api/task-helper/initialize/{TASK_ID}")

print("\n" + "=" * 50)
print("DIAGNOSIS: The task-helper page is getting 404 because")
print("it's calling a non-existent endpoint. We need to either:")
print("1. Fix the frontend to call /api/wait-node/initialize/")
print("2. Create a new /api/task-helper/initialize/ endpoint")
print("3. Create a generic /api/initialize/ endpoint")