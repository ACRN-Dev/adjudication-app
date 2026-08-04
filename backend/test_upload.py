"""Quick test: hit the batches endpoint and try an upload."""
import requests, os, sys

BASE = "http://127.0.0.1:8000/api/realtime"
HEADERS = {"X-Demo-User": "monitor1@acrnhealth.com", "X-Demo-Role": "MONITOR"}

# 1. List existing batches
print("=== LIST BATCHES ===")
r = requests.get(f"{BASE}/batches", headers=HEADERS)
print(f"Status: {r.status_code}")
print(f"Body: {r.text[:500]}")

# 2. List existing patients
print("\n=== LIST PATIENTS ===")
r = requests.get(f"{BASE}/patients", headers=HEADERS)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Total patients: {data.get('total', '?')}")
if data.get("items"):
    for p in data["items"][:3]:
        print(f"  - {p['subject_id']} | visits={p['visit_count']} | status={p['qc_status']}")

# 3. Try upload
csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rt", "Mutala_15_complete_subjects.csv")
if os.path.exists(csv_path):
    print(f"\n=== UPLOAD TEST ({os.path.basename(csv_path)}, {os.path.getsize(csv_path)//1024} KB) ===")
    with open(csv_path, "rb") as f:
        r = requests.post(f"{BASE}/batches", headers=HEADERS, files={"file": (os.path.basename(csv_path), f, "text/csv")})
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:500]}")
else:
    print(f"\nCSV not found at: {csv_path}")
    # list rt dir
    rt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rt")
    if os.path.isdir(rt_dir):
        print("Files in rt/:")
        for fn in os.listdir(rt_dir)[:10]:
            print(f"  {fn}")
