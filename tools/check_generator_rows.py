import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
from web.app import _normalize_record_for_generator
import importlib.util

gen_path = ROOT / 'tools' / 'generate_from_excel.py'
spec = importlib.util.spec_from_file_location('genmod', str(gen_path))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

rows_list, formula_count = mod.read_excel_rows(str(ROOT / 'docs' / 'Input XML electr ziekmeldinge.xlsx'), data_only=True)
print('Rows read by generator:', len(rows_list), 'formula_count=', formula_count)
for i, rec in enumerate(rows_list[:8], start=2):
    norm = _normalize_record_for_generator(rec)
    print('Row', i, 'rec keys:', list(rec.keys()))
    print('  raw Achternaam:', repr(rec.get('Achternaam')))
    print('  norm Achternaam:', repr(norm.get('Achternaam')))
    print('  norm Naam:', repr(norm.get('Naam')), 'BSN:', repr(norm.get('BSN')), 'DatEersteAoDag:', repr(norm.get('DatEersteAoDag')))

print('done')
