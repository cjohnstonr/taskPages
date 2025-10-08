import requests
from datetime import datetime

TASK_ID = "868fkbrfv" 
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

# Test with correct dropdown value
custom_fields = [
    {"id": "c6e0281e-9001-42d7-a265-8f5da6b71132", "value": "TEST: Escalation reason"},
    {"id": "e9e831f2-b439-4067-8e88-6b715f4263b2", "value": "TEST: AI Summary"}, 
    {"id": "8d784bd0-18e5-4db3-b45e-9a2900262e04", "value": "Escalated"},
    {"id": "5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f", "value": int(datetime.now().timestamp() * 1000)}
]

print(f"Setting escalation fields on task {TASK_ID}")

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
        print("\n✅ Fields after update:")
        for cf in task.get('custom_fields', []):
            if cf['id'] in ['c6e0281e-9001-42d7-a265-8f5da6b71132', 'e9e831f2-b439-4067-8e88-6b715f4263b2', 
                           '8d784bd0-18e5-4db3-b45e-9a2900262e04', '5ffd2b3e-b8dc-4bd0-819a-a3d4c3396a5f']:
                print(f"  {cf.get('name')}: {cf.get('value')}")
else:
    print(f"❌ Error: {response.text}")
