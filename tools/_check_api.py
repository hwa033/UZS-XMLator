import urllib.request

endpoints = ["/", "/ready", "/api/health", "/api/xml/valideer", "/api/test/laatste"]
base = "http://127.0.0.1:5000"

for p in endpoints:
    url = base + p
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT)", "Accept": "*/*"}
        if p == "/api/xml/valideer":
            hdrs = headers.copy()
            hdrs["Content-Type"] = "application/xml"
            req = urllib.request.Request(url, data=b'<root/>', headers=hdrs, method='POST')
        else:
            req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as r:
            body = r.read().decode('utf-8', errors='replace')
            print(f"{p} -> {r.status}\n{body[:200]}\n")
    except Exception as e:
        print(f"{p} -> ERROR: {e}\n")
