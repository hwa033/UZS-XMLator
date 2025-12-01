import zipfile
import sys
p = sys.argv[1] if len(sys.argv)>1 else r"web/static/downloads/bulk_Digipoort_20251128131419.zip"
try:
    with zipfile.ZipFile(p) as z:
        names = z.namelist()
        print('ZIP:', p)
        print('NAMES:', names)
        if not names:
            print('zip empty')
            sys.exit(0)
        data = z.read(names[0])
        txt = data.decode('utf-8', errors='replace')
        print('\n---SNIPPET---\n')
        print('\n'.join(txt.splitlines()[:400]))
except Exception as e:
    print('ERROR', e)
