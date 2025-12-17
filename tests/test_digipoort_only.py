import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web.app import app
import io

c = app.test_client()

excel_path = ROOT / 'docs' / 'Input XML electr ziekmeldingen.xlsx'

# Test Digipoort
print("\n=== Test Digipoort ===")
with open(excel_path, 'rb') as f:
    excel_bytes = f.read()
data = {
    'excel_file': (io.BytesIO(excel_bytes), 'test.xlsx'),
    'aanvraag_type': 'Digipoort'
}
r = c.post('/upload_excel', data=data, headers={'X-Requested-With': 'XMLHttpRequest'})
print('Status:', r.status_code)
if r.is_json:
    print('Response:', r.get_json())

# Check the latest file
import os
out_dir = ROOT / 'build' / 'excel_generated'
recent_files = []
for fname in os.listdir(out_dir):
    if fname.endswith('.xml'):
        fpath = out_dir / fname
        mtime = os.path.getmtime(fpath)
        recent_files.append((fname, mtime))

recent_files.sort(key=lambda x: x[1], reverse=True)
fname, _ = recent_files[0]
print(f"\nNieuwste bestand: {fname}")
with open(out_dir / fname, 'r', encoding='utf-8') as f:
    content = f.read()
    if '<CdBerichtType>' in content:
        start = content.find('<CdBerichtType>') + len('<CdBerichtType>')
        end = content.find('</CdBerichtType>')
        cd_type = content[start:end]
        print(f"  CdBerichtType: {cd_type}")
    if '<ApplicatieNaam>' in content:
        start = content.find('<ApplicatieNaam>') + len('<ApplicatieNaam>')
        end = content.find('</ApplicatieNaam>')
        app_name = content[start:end]
        print(f"  ApplicatieNaam: {app_name}")
