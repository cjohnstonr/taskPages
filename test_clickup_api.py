#!/usr/bin/env python3
"""
Test script to investigate real ClickUp API comment response structure
"""

import os
import sys
import json
import requests
from pathlib import Path

# Add backend directory to path to import modules
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')
CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"

def test_clickup_comments_api():
    """Test ClickUp comments API with real task IDs to understand data structure"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY environment variable not found!")
        print("Please check backend/.env file")
        return None
    
    print(f"🔑 Using ClickUp API Key: {CLICKUP_API_KEY[:10]}...")
    print(f"👥 Team ID: {CLICKUP_TEAM_ID}")
    
    # Test task IDs from the debug logs
    test_tasks = [
        "868fkbmkj",  # Main task
        "868fkbmn7",  # Step task
        "868fkbrfv",  # Alternative task ID
    ]
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    for task_id in test_tasks:
        print(f"\n🔍 Testing task: {task_id}")
        print("=" * 50)
        
        # Test comments endpoint
        try:
            url = f"{CLICKUP_BASE_URL}/task/{task_id}/comment"
            params = {
                "team_id": CLICKUP_TEAM_ID,
                "limit": 3
            }
            
            print(f"📡 API Call: {url}")
            print(f"📋 Params: {params}")
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            print(f"📊 Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📝 Response keys: {list(data.keys())}")
                
                comments = data.get('comments', [])
                print(f"💬 Comments count: {len(comments)}")
                
                if comments:
                    # Analyze first comment structure
                    first_comment = comments[0]
                    print(f"\n🔬 First comment structure:")
                    print(json.dumps(first_comment, indent=2, default=str))
                    
                    # Document field mappings
                    print(f"\n📋 Field Analysis:")
                    print(f"  - ID: {first_comment.get('id')}")
                    print(f"  - Text field: 'comment_text' = {bool(first_comment.get('comment_text'))}")
                    print(f"  - Alt text field: 'text' = {bool(first_comment.get('text'))}")
                    print(f"  - Date field: 'date' = {first_comment.get('date')} (type: {type(first_comment.get('date'))})")
                    print(f"  - User structure: {first_comment.get('user', {}).keys() if first_comment.get('user') else 'None'}")
                    
                    if first_comment.get('user'):
                        user = first_comment['user']
                        print(f"    - Username: {user.get('username')}")
                        print(f"    - Initials: {user.get('initials')}")
                        print(f"    - Color: {user.get('color')}")
                        print(f"    - Email: {user.get('email')}")
                
                else:
                    print("ℹ️  No comments found for this task")
                    
            elif response.status_code == 404:
                print("❌ Task not found")
            elif response.status_code == 401:
                print("❌ Unauthorized - check API key")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"📄 Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Exception: {e}")
            
    return True

if __name__ == "__main__":
    print("🚀 ClickUp API Comments Structure Investigation")
    print("=" * 60)
    test_clickup_comments_api()