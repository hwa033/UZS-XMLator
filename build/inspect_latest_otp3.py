import zipfile, glob, os, sys
files = glob.glob('web/static/downloads/bulk_OTP3_*.zip')
if not files:
    print('No OTP3 zips found')
    sys.exit(1)
files = sorted(files, key=lambda p: os.path.getmtime(p), reverse=True)
p = files[0]
print('Using:', p)
with zipfile.ZipFile(p) as z:
    names = z.namelist()
    print('Names:', names)
    if not names:
        print('zip empty')
        sys.exit(0)
    txt = z.read(names[0]).decode('utf-8', errors='replace')
    print('\n---SNIPPET---\n')
    print('\n'.join(txt.splitlines()[:200]))
