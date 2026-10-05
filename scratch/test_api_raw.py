import urllib.request

try:
    req = urllib.request.Request("http://localhost:8000/patients?page=1&page_size=5")
    req.add_header("x-demo-user", "tinotenda@example.com")
    req.add_header("x-demo-role", "MONITOR")
    with urllib.request.urlopen(req, timeout=5) as resp:
        print("Status:", resp.status)
        print("Body:", resp.read()[:200])
except urllib.error.HTTPError as e:
    print("HTTPError:", e.code, e.read()[:200])
except Exception as e:
    print("Error:", e)
