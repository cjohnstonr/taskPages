import requests

TASK_ID = "868fkbrfv"
API_KEY = 'pk_120213011_5ZNEENWOLLDGUG3C5EA40CE41C5O91XB'

response = requests.get(
    f"https://api.clickup.com/api/v2/task/{TASK_ID}",
    headers={"Authorization": API_KEY}
)

if response.ok:
    task = response.json()
    for cf in task.get('custom_fields', []):
        if cf['id'] == '8d784bd0-18e5-4db3-b45e-9a2900262e04':  # ESCALATION_STATUS
            print("ESCALATION_STATUS dropdown options:")
            for option in cf.get('type_config', {}).get('options', []):
                print(f"  - Name: '{option['name']}' -> UUID: '{option['id']}'")
