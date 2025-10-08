#!/usr/bin/env python3
"""Check what custom field 56d8c645-1e50-421c-bb62-1e3ef1cff80f is"""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

backend_path = Path(__file__).parent / 'backend'
load_dotenv(backend_path / '.env')

CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY')
CLICKUP_TEAM_ID = os.getenv('CLICKUP_TEAM_ID', '9011954126')
FIELD_ID = '56d8c645-1e50-421c-bb62-1e3ef1cff80f'

if CLICKUP_API_KEY:
    headers = {"Authorization": CLICKUP_API_KEY}
    
    # Get team custom fields
    url = f"https://api.clickup.com/api/v2/team/{CLICKUP_TEAM_ID}/field"
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        fields = data.get('fields', [])
        
        # Find our specific field
        for field in fields:
            if field.get('id') == FIELD_ID:
                print(f"✅ Found field: {field.get('name')}")
                print(f"   Type: {field.get('type')}")
                print(f"   ID: {field.get('id')}")
                break
        else:
            print(f"❌ Field {FIELD_ID} not found in team custom fields")
    else:
        print(f"API Error: {response.status_code}")
else:
    print("No API key found")