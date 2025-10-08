import requests

TASK_ID = "868fkbrfv" 
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

# Test setting just the status field
custom_fields = [
    {"id": "8d784bd0-18e5-4db3-b45e-9a2900262e04", "value": "pending"}
]

print(f"Setting ESCALATION_STATUS to 'pending' on task {TASK_ID}")

response = requests.put(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": API_KEY, "Content-Type": "application/json"},
    json={"custom_fields": custom_fields}
)

print(f"Response: {response.status_code}")
if response.ok:
    # Fetch to verify
    get_resp = requests.get(
        f"https://api.clickup.com/api/v2/task/{TASK_ID}",
        headers={"Authorization": API_KEY}
    )
    if get_resp.ok:
        task = get_resp.json()
        for cf in task.get('custom_fields', []):
            if cf['id'] == '8d784bd0-18e5-4db3-b45e-9a2900262e04':
                print(f"✅ Field value after update: {cf.get('value')}")
                print(f"   Type: {cf.get('type')}, Name: {cf.get('name')}")
                if 'type_config' in cf:
                    print(f"   Options: {cf.get('type_config', {}).get('options', [])}")
else:
    print(f"❌ Error: {response.text}")
