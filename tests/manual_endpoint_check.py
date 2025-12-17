import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web.app import app

c = app.test_client()

r = c.get('/genereer_xml')
print('genereer_xml', r.status_code)

r = c.get('/resultaten/fragment')
print('fragment', r.status_code, len(r.get_data()))

fn = 'zbm_555501759_20251215_175243.xml'
r = c.get('/resultaten/preview/' + fn)
print('preview', r.status_code, r.is_json)
print('preview_keys', list((r.get_json() or {}).keys()))

# Test download zip via test client
samples = []
try:
	import os
	out_dir = ROOT / 'build' / 'excel_generated'
	for name in os.listdir(out_dir):
		if name.endswith('.xml'):
			samples.append(name)
		if len(samples) >= 2:
			break
except Exception as e:
	print('list excel_generated failed:', e)

if samples:
	import json as _json
	r = c.post('/resultaten/download-zip', data=_json.dumps({'filenames': samples}), content_type='application/json')
	print('zip', r.status_code, r.headers.get('Content-Type'), int(r.headers.get('Content-Length') or 0) > 0)
else:
	print('zip skipped: no sample xmls found')
