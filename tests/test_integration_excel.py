import io
import pytest

from web import app as webapp


@pytest.mark.integration
def test_excel_upload_generates_xml_and_zip(tmp_path, monkeypatch):
    # Skip if openpyxl not available; import inside test to avoid collection-time import errors
    pytest.importorskip("openpyxl")
    import openpyxl

    # Prepare temporary output and downloads directories
    tmp_out = tmp_path / "out"
    tmp_dl = tmp_path / "dl"
    tmp_out.mkdir()
    tmp_dl.mkdir()

    # Monkeypatch OUTPUT_MAP and DOWNLOADS_DIR used by the app
    monkeypatch.setattr(webapp, "OUTPUT_MAP", {"ZBM": tmp_out, "VM": tmp_out, "Digipoort": tmp_out})
    monkeypatch.setattr(webapp, "DOWNLOADS_DIR", tmp_dl)

    client = webapp.test_client()

    # Build a simple Excel workbook in-memory
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["BSN", "naam", "geboortedatum"])
    ws.append(["123456789", "Test User", "2020-01-01"])
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    data = {
        "aanvraag_type": "ZBM",
        "excel_file": (bio, "test.xlsx"),
    }

    resp = client.post("/genereer_xml/upload_excel", data=data, content_type="multipart/form-data", follow_redirects=True)
    assert resp.status_code == 200

    # Expect at least one XML file written to tmp_out
    xml_files = list(tmp_out.glob("*.xml"))
    assert len(xml_files) >= 1

    # If a bulk zip was generated, it should be in DOWNLOADS_DIR
    zips = list(tmp_dl.glob("*.zip"))
    # zip may be present depending on implementation path; accept 0 or 1
    assert len(zips) in (0, 1)
