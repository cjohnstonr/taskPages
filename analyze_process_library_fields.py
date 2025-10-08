#!/usr/bin/env python3
"""
Script to analyze all custom fields for a Process Library task
and save the results to zprocesslibrarytaskjson.md
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from backend/.env
backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')

# The task ID to analyze
CUSTOM_TASK_ID = 'TICKET-69453'

def get_process_library_task(custom_task_id):
    """Get complete task details including all custom fields"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found in backend/.env")
        return None
    
    print(f"🔍 Fetching task: {custom_task_id}")
    print(f"👥 Team ID: {CLICKUP_TEAM_ID}")
    print("=" * 60)
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    # For custom task IDs, we need to include team_id and custom_task_ids=true
    url = f"https://api.clickup.com/api/v2/task/{custom_task_id}"
    params = {
        "team_id": CLICKUP_TEAM_ID,
        "custom_task_ids": "true",
        "include_subtasks": "false"
    }
    
    try:
        print(f"📡 Calling: {url}")
        print(f"📋 Parameters: {params}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            task_data = response.json()
            
            print("✅ Task fetched successfully!")
            print(f"Task Name: {task_data.get('name')}")
            print(f"Task ID: {task_data.get('id')}")
            print(f"Custom ID: {task_data.get('custom_id')}")
            print(f"Custom Item ID (Type): {task_data.get('custom_item_id')}")
            print("=" * 60)
            
            # Analyze custom fields
            custom_fields = task_data.get('custom_fields', [])
            print(f"\n📊 Found {len(custom_fields)} custom fields")
            
            # Create markdown report
            create_markdown_report(task_data, custom_fields)
            
            return task_data
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 Exception: {e}")
        return None

def create_markdown_report(task_data, custom_fields):
    """Create a detailed markdown report of the task and its custom fields"""
    
    md_content = []
    md_content.append("# Process Library Task Analysis")
    md_content.append(f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_content.append(f"\n## Task Information")
    md_content.append(f"- **Name:** {task_data.get('name')}")
    md_content.append(f"- **ID:** {task_data.get('id')}")
    md_content.append(f"- **Custom ID:** {task_data.get('custom_id')}")
    md_content.append(f"- **Custom Item ID (Type):** {task_data.get('custom_item_id')}")
    md_content.append(f"- **Status:** {task_data.get('status', {}).get('status')}")
    
    md_content.append(f"\n## Custom Fields Summary ({len(custom_fields)} fields)\n")
    
    # Group fields by type
    fields_by_type = {}
    for field in custom_fields:
        field_type = field.get('type', 'unknown')
        if field_type not in fields_by_type:
            fields_by_type[field_type] = []
        fields_by_type[field_type].append(field)
    
    # Summary table
    md_content.append("| Type | Count | Field Names |")
    md_content.append("|------|-------|-------------|")
    for field_type, fields in sorted(fields_by_type.items()):
        field_names = ", ".join([f.get('name', 'unnamed') for f in fields])
        md_content.append(f"| {field_type} | {len(fields)} | {field_names} |")
    
    md_content.append(f"\n## Detailed Custom Fields\n")
    
    # Detailed field information
    for idx, field in enumerate(custom_fields, 1):
        md_content.append(f"### {idx}. {field.get('name', 'Unnamed Field')}")
        md_content.append(f"- **Field ID:** `{field.get('id')}`")
        md_content.append(f"- **Type:** `{field.get('type')}`")
        md_content.append(f"- **Required:** {field.get('required', False)}")
        md_content.append(f"- **Hide from guests:** {field.get('hide_from_guests', False)}")
        
        # Field value
        value = field.get('value')
        if value is not None:
            if isinstance(value, (list, dict)):
                md_content.append(f"- **Value:** ```json\n{json.dumps(value, indent=2)}\n```")
            else:
                md_content.append(f"- **Value:** `{value}`")
        else:
            md_content.append(f"- **Value:** *(empty)*")
        
        # Type configuration
        type_config = field.get('type_config')
        if type_config:
            md_content.append(f"- **Type Config:** ```json\n{json.dumps(type_config, indent=2)}\n```")
        
        md_content.append("")
    
    # Raw JSON at the end
    md_content.append("\n## Raw Task JSON\n")
    md_content.append("```json")
    md_content.append(json.dumps(task_data, indent=2))
    md_content.append("```")
    
    # Write to file
    output_file = 'zprocesslibrarytaskjson.md'
    with open(output_file, 'w') as f:
        f.write('\n'.join(md_content))
    
    print(f"\n💾 Report saved to {output_file}")
    
    # Also save raw JSON for processing
    json_file = 'zprocesslibrarytask.json'
    with open(json_file, 'w') as f:
        json.dump(task_data, f, indent=2)
    print(f"💾 Raw JSON saved to {json_file}")

def analyze_field_types(custom_fields):
    """Analyze and categorize field types"""
    
    print("\n📈 Field Type Analysis:")
    print("=" * 40)
    
    # Count by type
    type_counts = {}
    for field in custom_fields:
        field_type = field.get('type', 'unknown')
        type_counts[field_type] = type_counts.get(field_type, 0) + 1
    
    # Display counts
    for field_type, count in sorted(type_counts.items()):
        print(f"  {field_type}: {count} field(s)")
    
    # Show fields with values
    print("\n🔍 Fields with values:")
    for field in custom_fields:
        if field.get('value') is not None:
            value_preview = str(field.get('value'))[:50]
            if len(str(field.get('value'))) > 50:
                value_preview += "..."
            print(f"  - {field.get('name')}: {value_preview}")

if __name__ == "__main__":
    print("🚀 Process Library Task Custom Fields Analyzer")
    print("=" * 60)
    
    task_data = get_process_library_task(CUSTOM_TASK_ID)
    
    if task_data:
        custom_fields = task_data.get('custom_fields', [])
        analyze_field_types(custom_fields)
        print("\n✅ Analysis complete!")
        print(f"📄 Check zprocesslibrarytaskjson.md for the full report")
    else:
        print("\n❌ Failed to fetch task data")