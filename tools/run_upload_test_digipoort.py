import sys
from pathlib import Path
import io

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from web.app import app

EXCEL = ROOT / 'docs' / 'Input XML electr ziekmeldinge.xlsx'
if not EXCEL.exists():
    print('ERROR: sample Excel not found at', EXCEL)
    raise SystemExit(1)

content = EXCEL.read_bytes()

with app.test_client() as client:
    data = {
        'aanvraag_type': 'Digipoort',
        'validate': 'on',
        'excel_file': (io.BytesIO(content), EXCEL.name),
    }
    resp = client.post('/genereer_xml/upload_excel', data=data, content_type='multipart/form-data', follow_redirects=True)
    print('Status:', resp.status)
    out = ROOT / 'build' / 'test_upload_response_digipoort.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.get_data())
    print('Wrote response HTML to', out)
    txt = resp.get_data(as_text=True)
    import re
    fns = re.findall(r'([\w\-]+_\d{8}_\d{6}\.xml)', txt)
    print('Found generated filenames:', fns)
    errs = re.findall(r'Regel \d+: [^<\n]+', txt)
    if errs:
        print('\nErrors found:')
        for e in errs:
            print('-', e)
    else:
        print('No per-row errors found')

print('Done')
