import urllib.request
import json

try:
    req = urllib.request.Request("http://localhost:8000/patients?page=1&page_size=5")
    # Add demo headers
    req.add_header("x-demo-user", "tinotenda@example.com")
    req.add_header("x-demo-role", "MONITOR")
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        print("API Response /patients:")
        print("  Type:", type(data))
        if isinstance(data, list):
            print(f"  Returned {len(data)} patients")
            for p in data[:3]:
                print(f"    Subj: {p.get('subject_id')} | Age: {p.get('age')}")
        elif isinstance(data, dict):
            print("  Keys:", list(data.keys()))
except Exception as e:
    print("API request failed:", e)
