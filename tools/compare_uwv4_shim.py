from pathlib import Path
import re
uwv_body = Path(__file__).parent.parent / 'docs' / 'UwvZwMeldingInternBody-v0428-b01.xsd'
shim = Path(__file__).parent.parent / 'docs' / 'UwvML-BaseTypes-v0441.xsd'
s = uwv_body.read_text(encoding='utf-8')
shim_s = shim.read_text(encoding='utf-8')
uwv4=set(re.findall(r'uwv4:([A-Za-z0-9_]+)', s))
shim_types=set(re.findall(r'name="([A-Za-z0-9_]+)"', shim_s))
missing = sorted([t for t in uwv4 if t not in shim_types])
print('missing', len(missing))
for m in missing:
    print(m)
