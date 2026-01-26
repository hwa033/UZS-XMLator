import io
import json
import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))  # noqa: E402

from web.app import app

# Sample JSON payload
payload = {
    "aanvraag_type": "Digipoort",
    "BSN": "555501759",
    "Voorletters": "J",
    "Achternaam": "Test",
    "Geboortedatum": "1980-01-01",
    "DatumAangifte": "2025-12-05",
    "DatumVanaf": "2025-12-01",
}

content = json.dumps(payload).encode("utf-8")

with app.test_client() as client:
    data = {
        "aanvraag_type": "Digipoort",
        "validate": "on",
        "json_file": (io.BytesIO(content), "sample.json"),
    }
    resp = client.post(
        "/genereer_xml_json/upload_json",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    print("Status:", resp.status)
    out = ROOT / "build" / "test_upload_response_json.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(resp.get_data())
    print("Wrote response HTML to", out)
    txt = resp.get_data(as_text=True)
    import re

    fns = re.findall(r"([\w\-]+_\d{8}_\d{6}\.xml)", txt)
    print("Found generated filenames:", fns)

print("Done")
