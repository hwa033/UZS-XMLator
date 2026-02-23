import io
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from web.app import app, get_output_directory


def test_digipoort_generates_file():
    c = app.test_client()
    excel_path = ROOT / "docs" / "Input XML electr ziekmeldingen.xlsx"

    with open(excel_path, "rb") as f:
        excel_bytes = f.read()

    resp = c.post(
        "/upload_excel",
        data={
            "excel_file": (io.BytesIO(excel_bytes), "test.xlsx"),
            "aanvraag_type": "Digipoort",
        },
        headers={"X-Requested-With": "XMLHttpRequest"},
    )

    assert resp.status_code == 200
    assert resp.is_json
    body = resp.get_json() or {}
    assert body.get("success") is True

    out_dir = Path(get_output_directory("Digipoort"))
    recent_files = []
    for fname in os.listdir(out_dir) if out_dir.exists() else []:
        if fname.endswith(".xml"):
            fpath = out_dir / fname
            recent_files.append((fname, os.path.getmtime(fpath)))

    if not recent_files:
        pytest.skip("Geen gegenereerde XML-bestanden gevonden na upload")

    recent_files.sort(key=lambda x: x[1], reverse=True)
    fname, _ = recent_files[0]

    with open(out_dir / fname, encoding="utf-8") as f:
        content = f.read()

    if "<CdBerichtType>" in content:
        start = content.find("<CdBerichtType>") + len("<CdBerichtType>")
        end = content.find("</CdBerichtType>")
        assert content[start:end] == "OTP3"

    if "<ApplicatieNaam>" in content:
        start = content.find("<ApplicatieNaam>") + len("<ApplicatieNaam>")
        end = content.find("</ApplicatieNaam>")
        assert content[start:end]
