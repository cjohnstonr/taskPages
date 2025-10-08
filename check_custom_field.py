#!/usr/bin/env python3
"""
Quick script to check the name of a specific ClickUp custom field
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

# The custom field ID we want to check
PROCESS_TEXT_FIELD_ID = 'b2587292-c1bc-4ee0-8dcb-a69db68d5fe8'

def get_team_custom_fields():
    """Get all custom fields for the team to find our specific field"""
    
    if not CLICKUP_API_KEY:
        print("❌ ERROR: CLICKUP_API_KEY not found in backend/.env")
        return None
    
    print(f"🔍 Searching for custom field: {PROCESS_TEXT_FIELD_ID}")
    print(f"👥 Team ID: {CLICKUP_TEAM_ID}")
    print("=" * 60)
    
    headers = {
        "Authorization": CLICKUP_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Get team custom fields
    url = f"https://api.clickup.com/api/v2/team/{CLICKUP_TEAM_ID}/field"
    
    try:
        print(f"📡 Calling: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            fields = data.get('fields', [])
            
            print(f"✅ Found {len(fields)} custom fields in team")
            print("=" * 60)
            
            # Find our specific field
            for field in fields:
                if field.get('id') == PROCESS_TEXT_FIELD_ID:
                    print("🎯 FOUND THE FIELD!")
                    print(f"  Field Name: {field.get('name')}")
                    print(f"  Field ID: {field.get('id')}")
                    print(f"  Field Type: {field.get('type')}")
                    print(f"  Field Config: {json.dumps(field.get('type_config', {}), indent=2)}")
                    return field
            
            print(f"⚠️  Field ID {PROCESS_TEXT_FIELD_ID} not found in team fields")
            print("\n📋 All available fields:")
            for field in fields:
                print(f"  - {field.get('name')}: {field.get('id')}")
                
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")
    
    return None

if __name__ == "__main__":
    print("🚀 ClickUp Custom Field Name Checker")
    print("=" * 60)
    field_info = get_team_custom_fields()
    
    if field_info:
        print("\n✅ SUCCESS! The custom field name is:", field_info.get('name'))