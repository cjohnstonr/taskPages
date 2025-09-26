import requests

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

# Test setting status with UUID
field_id = "8d784bd0-18e5-4db3-b45e-9a2900262e04"
print("Setting ESCALATION_STATUS to 'Escalated' using UUID...")

response = requests.post(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}/field/{field_id}",
    headers={
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    },
    json={"value": "8dc15846-e8c7-43a8-b7b2-1e1a0e1d6497"}  # UUID for 'Escalated'
)

print(f"Status: {response.status_code}")
if response.ok:
    print("✅ SUCCESS\!")
else:
    print(f"❌ Error: {response.text}")
    
# Verify it was set
get_response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": API_KEY}
)

if get_response.ok:
    task = get_response.json()
    for cf in task.get('custom_fields', []):
        if cf['id'] == '8d784bd0-18e5-4db3-b45e-9a2900262e04':
            value = cf.get('value')
            print(f"\nESCALATION_STATUS is now: {value}")
