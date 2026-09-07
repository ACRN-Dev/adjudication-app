from fastapi.testclient import TestClient
from main import app

client = TestClient(app)
r = client.get("/api/realtime/patients", headers={"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR"})
print("STATUS:", r.status_code)
print("TEXT:", r.text)
