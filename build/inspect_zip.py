import zipfile
import sys
p = r"web/static/downloads/bulk_Digipoort_20251128131419.zip"
try:
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        print('NAMES:', names)
        if not names:
            print('zip empty')
            sys.exit(0)
        data = z.read(names[0])
        txt = data.decode('utf-8', errors='replace')
        print('\n---SNIPPET---\n')
        print('\n'.join(txt.splitlines()[:200]))
except Exception as e:
    print('ERROR', e)