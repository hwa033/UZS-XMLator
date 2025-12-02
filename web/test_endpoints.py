import urllib.request

paths = ["/ping", "/debug/routes", "/instellingen/"]
for p in paths:
    url = f"http://127.0.0.1:5000{p}"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read(2000).decode("utf-8", errors="replace")
            print(f"{p} -> {resp.status}\n", body[:1000])
    except Exception as e:
        print(f"{p} -> ERROR: {e}")
