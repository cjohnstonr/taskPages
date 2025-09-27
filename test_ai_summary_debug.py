#!/usr/bin/env python3
"""
Test script to reproduce AI Summary NoneType error
Based on the forensic analysis of commit a07a1c6
"""

import requests
import json
import os
from datetime import datetime

# Test configuration
BACKEND_URL = "http://localhost:5000"
TASK_ID = "867h81m5j"  # Use a real task ID for testing

# Mock task context that might be causing the NoneType error
test_contexts = [
    # Test 1: Normal context (should work)
    {
        "name": "Normal Context",
        "context": {
            "task": {
                "id": TASK_ID,
                "name": "Test Task",
                "status": {"status": "to do", "type": "open"},
                "priority": {"priority": "high"},
                "assignees": [{"username": "testuser"}],
                "due_date": "2025-10-01",
                "description": "Test task description"
            },
            "parent_task": {
                "name": "Parent Task"
            }
        }
    },
    
    # Test 2: Context with None task (likely broken)
    {
        "name": "None Task Context",
        "context": {
            "task": None,
            "parent_task": None
        }
    },
    
    # Test 3: Context with None nested objects (potential issue)
    {
        "name": "None Nested Objects",
        "context": {
            "task": {
                "id": TASK_ID,
                "name": "Test Task",
                "status": None,  # This might cause .get() on None
                "priority": None,  # This might cause .get() on None
                "assignees": None,  # This might cause iteration on None
                "due_date": None,
                "description": None
            },
            "parent_task": None
        }
    },
    
    # Test 4: Empty context (edge case)
    {
        "name": "Empty Context", 
        "context": {}
    },
    
    # Test 5: Missing task key (edge case)
    {
        "name": "Missing Task Key",
        "context": {
            "parent_task": None
        }
    }
]

def test_ai_summary_endpoint():
    """Test the AI summary endpoint with various context scenarios"""
    
    print("=" * 60)
    print("AI SUMMARY FORENSIC TESTING")
    print("=" * 60)
    print(f"Testing endpoint: {BACKEND_URL}/api/ai/generate-escalation-summary")
    print(f"Task ID: {TASK_ID}")
    print()
    
    # Test each context scenario
    for i, test_case in enumerate(test_contexts, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 40)
        
        payload = {
            "task_id": TASK_ID,
            "reason": f"TEST ESCALATION - {test_case['name']}",
            "context": test_case['context']
        }
        
        try:
            print(f"Sending payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{BACKEND_URL}/api/ai/generate-escalation-summary",
                json=payload,
                timeout=30
            )
            
            print(f"Status Code: {response.status_code}")
            
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                
                if response.status_code == 200 and response_data.get('success'):
                    print("✅ SUCCESS: AI summary generated successfully")
                else:
                    print("❌ FAILED: AI summary generation failed")
                    if 'error' in response_data:
                        print(f"Error: {response_data['error']}")
                    if 'technical_error' in response_data:
                        print(f"Technical Error: {response_data['technical_error']}")
                        
                        # Check for the specific NoneType error
                        if "'NoneType' object has no attribute 'get'" in str(response_data['technical_error']):
                            print("🎯 FOUND THE NONETYPE ERROR!")
                            print("This test case reproduces the bug!")
                            
            except json.JSONDecodeError:
                print(f"Invalid JSON response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            
        print()
    
    print("=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print("The test case that reproduces the NoneType error indicates")
    print("the exact line where the bug occurs in the AI endpoint.")
    print("Look for patterns in the successful vs failed test cases.")

if __name__ == "__main__":
    test_ai_summary_endpoint()