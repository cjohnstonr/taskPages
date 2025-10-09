#!/usr/bin/env python3
"""
Test script to verify all escalation field IDs are accessible on a task.
Tests against TICKET-43999 with proper custom task ID handling.
"""

import os
import requests
import json
from typing import Optional, Dict, Any

# ClickUp Configuration
CLICKUP_API_KEY = os.getenv('CLICKUP_API_KEY', 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB')
TEAM_ID = '9011954126'
BASE_URL = 'https://api.clickup.com/api/v2'

HEADERS = {
    'Authorization': CLICKUP_API_KEY,
    'Content-Type': 'application/json'
}

# All 14 Escalation Field IDs from ESCALATION_FIELDS_ACTUAL.md
ESCALATION_FIELDS = {
    'ESCALATION_REASON_TEXT': 'c6e0281e-9001-42d7-a265-8f5da6b71132',
    'ESCALATION_REASON_AI': 'e9e831f2-b439-4067-8e88-6b715f4263b2',
    'ESCALATION_AI_SUGGESTION': 'bc5e9359-01cd-408f-adb9-c7bdf1f2dd29',
    'ESCALATION_STATUS': '8d784bd0-18e5-4db3-b45e-9a2900262e04',
    'ESCALATION_SUBMITTED_DATE_TIME': '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f',
    'ESCALATION_RESPONSE_TEXT': 'a077ecc9-1a59-48af-b2cd-42a63f5a7f86',
    'ESCALATION_RESOLVED_DATE_TIME': 'c40bf1c4-7d33-4b2b-8765-0784cd88591a',
    'ESCALATION_AI_GRADE': '629ca244-a6d3-46dd-9f1e-6a0ded40f519',
    'ESCALATION_HISTORY': '94790367-5d1f-4300-8f79-e13819f910d4',
    'ESCALATION_LEVEL': '90d2fec8-7474-4221-84c0-b8c7fb5e4385',  # Note: Has typo "Esclation_Level" in ClickUp
    'ESCALATION_RFI_STATUS': 'f94c0b4b-0c70-4c23-9633-07af2fa6ddc6',
    'ESCALATION_RFI_REQUEST': '0e7dd6f8-3167-4df5-964e-574734ffd4ed',
    'ESCALATION_RFI_RESPONSE': 'b5c52661-8142-45e0-bec5-14f3c135edbc',
    'PROPERTY_LINK': '73999194-0433-433d-a27c-4d9c5f194fd0'
}

# New ESCALATION_STATUS dropdown options (5 states)
ESCALATION_STATUS_OPTIONS = {
    0: {'id': 'bf10e6ce-bef9-4105-aa2c-913049e2d4ed', 'name': 'Not Escalated', 'color': '#FF4081'},
    1: {'id': '8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497', 'name': 'Escalated', 'color': '#7C4DFF'},
    2: {'id': 'cbf82936-5488-4612-93a7-f8161071b0eb', 'name': 'Resolved', 'color': '#f9d900'},
    3: {'id': '460769a8-90fa-401d-aeb1-a6d90fb3ee04', 'name': 'Escalated Level 2', 'color': '#3397dd'},
    4: {'id': 'ca62ea92-bc51-4d4a-93a8-c084e330e278', 'name': 'Awaiting Info', 'color': '#f900ea'}
}


def get_task(task_id: str) -> Dict[str, Any]:
    """
    Fetch task from ClickUp API with custom task ID support.

    Args:
        task_id: Task ID (TICKET-43999 format)

    Returns:
        Task data as dict
    """
    # For custom task IDs, MUST include these parameters
    params = {
        'team_id': TEAM_ID,
        'custom_task_ids': 'true'
    }

    url = f'{BASE_URL}/task/{task_id}'
    print(f"\n🔍 Fetching task: {task_id}")
    print(f"   URL: {url}")
    print(f"   Params: {params}")

    response = requests.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    return response.json()


def get_custom_field_value(task: Dict[str, Any], field_id: str) -> Optional[Any]:
    """
    Extract custom field value from task.

    Args:
        task: Task data dict
        field_id: Custom field ID to search for

    Returns:
        Field value or None if not found
    """
    custom_fields = task.get('custom_fields', [])
    for field in custom_fields:
        if field['id'] == field_id:
            value = field.get('value')
            # Return value even if empty (to distinguish from missing field)
            return value
    return None


def test_escalation_fields(task_id: str = 'TICKET-43999'):
    """
    Test all escalation field IDs on a specific task.

    Args:
        task_id: Task ID to test (default: TICKET-43999)
    """
    print("=" * 80)
    print("ESCALATION FIELDS VERIFICATION TEST")
    print("=" * 80)
    print(f"Task ID: {task_id}")
    print(f"Total Fields to Test: {len(ESCALATION_FIELDS)}")
    print()

    try:
        # Fetch the task
        task = get_task(task_id)
        print(f"✅ Task fetched successfully")
        print(f"   Task Name: {task['name']}")
        print(f"   Regular ID: {task['id']}")
        print(f"   Total Custom Fields: {len(task.get('custom_fields', []))}")
        print()

        # Test each escalation field
        results = {
            'found': [],
            'missing': [],
            'empty': []
        }

        print("-" * 80)
        print("FIELD VERIFICATION RESULTS")
        print("-" * 80)

        for field_name, field_id in ESCALATION_FIELDS.items():
            value = get_custom_field_value(task, field_id)

            if value is None:
                # Field exists but has no value
                print(f"⚪ {field_name}")
                print(f"   ID: {field_id}")
                print(f"   Status: EXISTS (no value set)")
                results['empty'].append(field_name)
            elif value == [] or value == '':
                # Field exists but is empty array/string
                print(f"⚪ {field_name}")
                print(f"   ID: {field_id}")
                print(f"   Status: EXISTS (empty value)")
                results['empty'].append(field_name)
            else:
                # Field exists and has value
                print(f"✅ {field_name}")
                print(f"   ID: {field_id}")

                # Special handling for dropdown fields
                if field_name == 'ESCALATION_STATUS':
                    option_info = ESCALATION_STATUS_OPTIONS.get(value, {'name': 'Unknown'})
                    print(f"   Value: {value} ({option_info['name']})")
                elif field_name == 'PROPERTY_LINK':
                    if isinstance(value, list):
                        print(f"   Value: [{len(value)} properties linked]")
                        if value:
                            print(f"   Properties: {[p.get('name', p.get('id')) for p in value]}")
                    else:
                        print(f"   Value: {value}")
                else:
                    # Truncate long text values
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + '...'
                    print(f"   Value: {value_str}")

                results['found'].append(field_name)

            print()

        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Fields with Values: {len(results['found'])}")
        if results['found']:
            for field in results['found']:
                print(f"   - {field}")
        print()

        print(f"⚪ Fields without Values: {len(results['empty'])}")
        if results['empty']:
            for field in results['empty']:
                print(f"   - {field}")
        print()

        print(f"❌ Missing Fields: {len(results['missing'])}")
        if results['missing']:
            for field in results['missing']:
                print(f"   - {field}")
        print()

        # Verification status
        total_accessible = len(results['found']) + len(results['empty'])
        if total_accessible == len(ESCALATION_FIELDS):
            print("✅ ALL FIELDS ACCESSIBLE - Phase 1 field verification PASSED")
        else:
            print(f"⚠️  ONLY {total_accessible}/{len(ESCALATION_FIELDS)} FIELDS ACCESSIBLE")

        print("=" * 80)

        # Test ESCALATION_STATUS dropdown specifically
        print("\n" + "=" * 80)
        print("ESCALATION_STATUS DROPDOWN VERIFICATION")
        print("=" * 80)

        status_value = get_custom_field_value(task, ESCALATION_FIELDS['ESCALATION_STATUS'])
        if status_value is not None:
            option = ESCALATION_STATUS_OPTIONS.get(status_value)
            if option:
                print(f"✅ Current Status: {option['name']} (orderindex: {status_value})")
                print(f"   Color: {option['color']}")
                print(f"   UUID: {option['id']}")
            else:
                print(f"⚠️  Unknown status value: {status_value}")
        else:
            print("⚪ Status not set on this task")

        print("\n📊 Available Status Options (5 states):")
        for idx, opt in ESCALATION_STATUS_OPTIONS.items():
            print(f"   {idx}. {opt['name']} (UUID: {opt['id']})")

        print("=" * 80)

        return results

    except requests.exceptions.RequestException as e:
        print(f"\n❌ API Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return None


if __name__ == '__main__':
    # Run test on TICKET-43999
    test_escalation_fields('TICKET-43999')
