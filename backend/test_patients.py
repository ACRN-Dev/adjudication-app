import requests

BASE = "http://127.0.0.1:8000/api/realtime"
HEADERS = {"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR"}

r = requests.get(f"{BASE}/patients", headers=HEADERS)
print(f"Status Code: {r.status_code}")
print(f"Response Text: {r.text}")
