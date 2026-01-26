import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import io

from web.app import app

c = app.test_client()

excel_path = ROOT / "docs" / "Input XML electr ziekmeldingen.xlsx"
with open(excel_path, "rb") as f:
    excel_bytes = f.read()

# Test ZBM
print("\n=== Test ZBM ===")
data = {"excel_file": (io.BytesIO(excel_bytes), "test.xlsx"), "aanvraag_type": "ZBM"}
r = c.post("/upload_excel", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
print("Status:", r.status_code)
if r.is_json:
    print("Response:", r.get_json())

# Test VM
print("\n=== Test VM ===")
excel_bytes2 = open(excel_path, "rb").read()
data = {"excel_file": (io.BytesIO(excel_bytes2), "test.xlsx"), "aanvraag_type": "VM"}
r = c.post("/upload_excel", data=data, headers={"X-Requested-With": "XMLHttpRequest"})
print("Status:", r.status_code)
if r.is_json:
    print("Response:", r.get_json())

# Check generated files
import os

out_dir = ROOT / "build" / "excel_generated"
recent_files = []
for fname in os.listdir(out_dir):
    if fname.endswith(".xml"):
        fpath = out_dir / fname
        mtime = os.path.getmtime(fpath)
        recent_files.append((fname, mtime))

recent_files.sort(key=lambda x: x[1], reverse=True)
print("\n=== Recent files (laatste 5) ===")
for fname, _ in recent_files[:5]:
    print(fname)
    # Check CdBerichtType and ApplicatieNaam in file
    with open(out_dir / fname, encoding="utf-8") as f:
        content = f.read()
        if "<CdBerichtType>" in content:
            start = content.find("<CdBerichtType>") + len("<CdBerichtType>")
            end = content.find("</CdBerichtType>")
            cd_type = content[start:end]
            print(f"  CdBerichtType: {cd_type}")
        if "<ApplicatieNaam>" in content:
            start = content.find("<ApplicatieNaam>") + len("<ApplicatieNaam>")
            end = content.find("</ApplicatieNaam>")
            app_name = content[start:end]
            print(f"  ApplicatieNaam: {app_name}")
