import urllib.request
import json

try:
    req = urllib.request.Request("http://127.0.0.1:8000/api/realtime/patients?page=1&page_size=5")
    req.add_header("x-demo-user", "coordinator@acrn.org")
    req.add_header("x-demo-role", "MONITOR_QC_REVIEWER")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print(f"Success! /api/realtime/patients returned {len(data)} patients:")
        for p in data:
            print(f"  Subject: {p.get('subject_id')} | Age: {p.get('age')} | Visits: {p.get('visit_count')}")
except Exception as e:
    print("API request failed:", e)
