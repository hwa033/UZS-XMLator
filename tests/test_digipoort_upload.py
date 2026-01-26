import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import io

from web.app import app

c = app.test_client()

# Create a minimal test Excel file for Digipoort upload test
# Read actual Excel file
excel_path = ROOT / "docs" / "Input XML electr ziekmeldingen.xlsx"
with open(excel_path, "rb") as f:
    excel_bytes = f.read()

# Simulate AJAX upload with Digipoort type
data = {
    "excel_file": (io.BytesIO(excel_bytes), "test.xlsx"),
    "aanvraag_type": "Digipoort",
}

r = c.post("/upload_excel", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
print("Status:", r.status_code)
print("Is JSON:", r.is_json)
if r.is_json:
    print("Response:", r.get_json())
else:
    print("Response (text):", r.get_data(as_text=True)[:500])
