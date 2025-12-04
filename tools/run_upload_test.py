import io
import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from web.app import app

EXCEL = ROOT / "docs" / "Input XML electr ziekmeldinge.xlsx"
if not EXCEL.exists():
    print("ERROR: sample Excel not found at", EXCEL)
    raise SystemExit(1)

content = EXCEL.read_bytes()

with app.test_client() as client:
    data = {
        # Use the Digipoort UI label in the form; the app maps this to OTP3
        "aanvraag_type": "Digipoort",
        "validate": "on",
        "excel_file": (io.BytesIO(content), EXCEL.name),
    }
    resp = client.post(
        "/genereer_xml/upload_excel",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    print("Status:", resp.status)
    out = ROOT / "build" / "test_upload_response.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.get_data())
    print("Wrote response HTML to", out)
    txt = resp.get_data(as_text=True)
    import re

    fns = re.findall(r"([\w\-]+_\d{8}_\d{6}\.xml)", txt)
    print("Found generated filenames:", fns)
    # Extract explicit error lines produced by our code
    errs = re.findall(r"Regel \d+: [^<\n]+", txt)
    if errs:
        print("\nErrors found:")
        for e in errs:
            print("-", e)
    else:
        m = re.search(r"Er waren\s*(\d+) fouten", txt)
        if m:
            print("Errors count:", m.group(1))

print("Done")
