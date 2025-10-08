#!/usr/bin/env python3
"""
Analyze custom fields for a Wait Node task and compare with Process Library fields
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

# The wait node task ID
WAIT_NODE_TASK_ID = 'TICKET-69459'

def get_wait_node_task(custom_task_id):
    """Get complete task details including all custom fields for wait node"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found in backend/.env")
        return None
    
    print(f"🔍 Fetching wait node task: {custom_task_id}")
    print(f"👥 Team ID: {CLICKUP_TEAM_ID}")
    print("=" * 60)
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    url = f"https://api.clickup.com/api/v2/task/{custom_task_id}"
    params = {
        "team_id": CLICKUP_TEAM_ID,
        "custom_task_ids": "true",
        "include_subtasks": "false"
    }
    
    try:
        print(f"📡 Calling: {url}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            task_data = response.json()
            
            print("✅ Wait node task fetched successfully!")
            print(f"Task Name: {task_data.get('name')}")
            print(f"Task ID: {task_data.get('id')}")
            print(f"Custom ID: {task_data.get('custom_id')}")
            print(f"Custom Item ID (Type): {task_data.get('custom_item_id')}")
            print("=" * 60)
            
            return task_data
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Exception: {e}")
        return None

def compare_with_process_library():
    """Compare wait node fields with process library fields"""
    
    # Load the previously saved Process Library task
    try:
        with open('zprocesslibrarytask.json', 'r') as f:
            process_task = json.load(f)
    except:
        print("⚠️ Could not load process library task for comparison")
        process_task = None
    
    # Get wait node task
    wait_task = get_wait_node_task(WAIT_NODE_TASK_ID)
    if not wait_task:
        return
    
    # Save wait node task
    with open('zwaitnodetask.json', 'w') as f:
        json.dump(wait_task, f, indent=2)
    print(f"💾 Wait node task saved to zwaitnodetask.json")
    
    # Analyze wait node fields
    wait_fields = wait_task.get('custom_fields', [])
    wait_fields_with_values = []
    
    for field in wait_fields:
        value = field.get('value')
        if value is not None and value != "" and value != [] and value != {}:
            wait_fields_with_values.append(field)
    
    print(f"\n📊 Wait Node Task Analysis:")
    print(f"Total Custom Fields: {len(wait_fields)}")
    print(f"Fields with values: {len(wait_fields_with_values)}")
    
    # Look for wait-specific fields
    wait_keywords = ['wait', 'approval', 'human', 'override', 'config', 'proposed']
    wait_specific_fields = []
    
    print("\n🎯 Wait Node Specific Fields (with values):")
    print("=" * 60)
    
    for field in wait_fields_with_values:
        name = field.get('name', 'unnamed')
        if any(keyword in name.lower() for keyword in wait_keywords):
            wait_specific_fields.append(field)
            field_type = field.get('type')
            field_id = field.get('id')
            value = field.get('value')
            
            # Format value for display
            if isinstance(value, str):
                value_display = value[:100] + "..." if len(value) > 100 else value
                value_display = value_display.replace('\n', ' ')
            elif isinstance(value, (list, dict)):
                value_display = json.dumps(value, indent=2)[:200] + "..."
            else:
                value_display = str(value)
            
            print(f"\n⭐ {name}")
            print(f"   Type: {field_type}")
            print(f"   ID: {field_id}")
            print(f"   Value: {value_display}")
    
    # Compare with Process Library fields if available
    if process_task:
        process_fields = process_task.get('custom_fields', [])
        process_field_ids = {f.get('id'): f.get('name') for f in process_fields}
        wait_field_ids = {f.get('id'): f.get('name') for f in wait_fields}
        
        # Find fields unique to wait node
        unique_to_wait = set(wait_field_ids.keys()) - set(process_field_ids.keys())
        
        if unique_to_wait:
            print("\n\n🔍 Fields UNIQUE to Wait Node (not in Process Library):")
            print("=" * 60)
            for field_id in unique_to_wait:
                field = next((f for f in wait_fields if f.get('id') == field_id), None)
                if field:
                    print(f"- {field.get('name')} ({field.get('type')})")
                    print(f"  ID: {field_id}")
    
    # Create detailed report
    with open('zwaitnodefieldanalysis.md', 'w') as f:
        f.write("# Wait Node vs Process Library Field Analysis\n\n")
        f.write(f"## Wait Node Task: {wait_task.get('name')}\n")
        f.write(f"- Custom ID: {wait_task.get('custom_id')}\n")
        f.write(f"- Task ID: {wait_task.get('id')}\n")
        f.write(f"- Custom Item ID: {wait_task.get('custom_item_id')}\n\n")
        
        f.write(f"## Field Statistics\n")
        f.write(f"- Total Fields: {len(wait_fields)}\n")
        f.write(f"- Fields with Values: {len(wait_fields_with_values)}\n")
        f.write(f"- Wait-Specific Fields: {len(wait_specific_fields)}\n\n")
        
        f.write("## Wait Node Specific Fields (with values)\n\n")
        for field in wait_specific_fields:
            name = field.get('name')
            field_type = field.get('type')
            field_id = field.get('id')
            value = field.get('value')
            
            f.write(f"### {name}\n")
            f.write(f"- **Type:** {field_type}\n")
            f.write(f"- **Field ID:** `{field_id}`\n")
            
            if isinstance(value, str):
                if len(value) > 500:
                    f.write(f"- **Value:** (truncated)\n```\n{value[:500]}...\n```\n\n")
                else:
                    f.write(f"- **Value:**\n```\n{value}\n```\n\n")
            elif isinstance(value, (list, dict)):
                f.write(f"- **Value:**\n```json\n{json.dumps(value, indent=2)}\n```\n\n")
            else:
                f.write(f"- **Value:** `{value}`\n\n")
        
        f.write("\n## All Fields with Values\n\n")
        f.write("| Field Name | Type | Value Preview |\n")
        f.write("|------------|------|---------------|\n")
        
        for field in wait_fields_with_values:
            name = field.get('name', 'unnamed')
            field_type = field.get('type')
            value = field.get('value')
            
            if isinstance(value, str):
                value_display = value[:50] + "..." if len(value) > 50 else value
                value_display = value_display.replace('\n', ' ').replace('|', '\\|')
            elif isinstance(value, list):
                value_display = f"[{len(value)} items]"
            elif isinstance(value, dict):
                value_display = f"{{dict}}"
            else:
                value_display = str(value)[:50]
            
            f.write(f"| {name} | {field_type} | {value_display} |\n")
    
    print(f"\n💾 Detailed analysis saved to zwaitnodefieldanalysis.md")

if __name__ == "__main__":
    print("🚀 Wait Node Task Custom Fields Analyzer")
    print("=" * 60)
    
    compare_with_process_library()
    
    print("\n✅ Analysis complete!")