import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from web.app import _normalize_record_for_generator
import openpyxl

EXCEL = ROOT / 'docs' / 'Input XML electr ziekmeldinge.xlsx'
wb = openpyxl.load_workbook(EXCEL, read_only=True, data_only=True)
s = wb.active
it = s.iter_rows(values_only=True)
headers = [h if h is not None else '' for h in next(it)]
print('Headers:', headers)
for idx, row in enumerate(it, start=2):
    rec = {h: v for h, v in zip(headers, row)}
    norm = _normalize_record_for_generator(rec)
    print('Row', idx, '->', {k: norm.get(k) for k in ('BSN','Naam','Achternaam','EersteVoornaam','DatEersteAoDag')})
    if idx>=8:
        break
