from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web import app

client = app.test_client()

to_check = ['/', '/ready', '/api/health', '/api/xml/throughput', '/api/xml/events', '/api/test/laatste']
for p in to_check:
    try:
        if p == '/api/xml/throughput':
            resp = client.get(p + '?days=3')
        else:
            resp = client.get(p)
        print(p, resp.status_code)
        data = None
        try:
            data = resp.get_json()
        except Exception:
            data = resp.get_data(as_text=True)[:300]
        print(data)
    except Exception as e:
        print(p, 'ERROR', e)
