import urllib.request
from pathlib import Path
import sys
ROOT = Path(__file__).parent.parent
DOCS = ROOT / 'docs'
DOCS.mkdir(parents=True, exist_ok=True)
urls = [
    'https://schemas.uwv.nl/UwvML/UwvML-BaseTypes-v0441.xsd',
    'http://schemas.uwv.nl/UwvML/UwvML-BaseTypes-v0441.xsd',
    'https://raw.githubusercontent.com/UZS-samples/UwvML-schemas/main/UwvML-BaseTypes-v0441.xsd',
    'https://raw.githubusercontent.com/uwv-nl/UwvML-schemas/main/UwvML-BaseTypes-v0441.xsd'
]
for u in urls:
    try:
        print('Trying', u)
        resp = urllib.request.urlopen(u, timeout=10)
        data = resp.read()
        if b'<xsd:schema' in data or b'<xs:schema' in data:
            out = DOCS / 'UwvML-BaseTypes-v0441.xsd'
            out.write_bytes(data)
            print('Saved to', out)
            sys.exit(0)
        else:
            print('Downloaded but content not recognized as XSD (len=%d)' % len(data))
    except Exception as e:
        print('Failed:', e)
print('All attempts failed')
sys.exit(2)
