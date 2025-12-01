import zipfile,os
p = os.path.join('web','static','downloads','bulk_Digipoort_20251128114028.zip')
if not os.path.exists(p):
    raise SystemExit('ZIP not found: '+p)
with zipfile.ZipFile(p) as z:
    names = z.namelist()
    print('Entries in ZIP:')
    for n in names:
        print('-', n)
    name = names[0]
    data = z.read(name)
    out = os.path.join('build','extracted2_Digipoort.xml')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out,'wb').write(data)
    print('\nWrote', out, '(entry:', name, ')')
    text = data.decode('utf-8')
    idx = text.find('CdBerichtType')
    if idx != -1:
        start = max(0, idx-200)
        end = min(len(text), idx+200)
        print('\nContext around CdBerichtType:')
        print(text[start:end])
    else:
        print('\nCdBerichtType not found in this XML')
    # Also print a small preview of the body
    body_idx = text.find('<SOAP-ENV:Body')
    if body_idx != -1:
        print('\n--- Body preview ---')
        print(text[body_idx:body_idx+2000])
