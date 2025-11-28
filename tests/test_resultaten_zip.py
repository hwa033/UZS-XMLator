import io
import json
import zipfile
from pathlib import Path

import pytest

import importlib

# Import the web.app module explicitly to avoid package-level `web.app` shadowing
app_module = importlib.import_module('web.app')

# The module exposes the Flask application as `app`
app = app_module.app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Ensure DOWNLOADS_DIR points to a temporary test folder
    test_dl = tmp_path / "downloads"
    test_dl.mkdir()
    monkeypatch.setattr(app_module, 'DOWNLOADS_DIR', test_dl)
    # also ensure OUTPUT_MAP contains the test folder for ease
    monkeypatch.setitem(app_module.OUTPUT_MAP, 'TEST', test_dl)
    with app.test_client() as c:
        yield c


def test_download_zip_contains_files(client):
    # create two small files in DOWNLOADS_DIR
    dl = app_module.DOWNLOADS_DIR
    f1 = dl / 'one.xml'
    f2 = dl / 'two.xml'
    f1.write_text('<root>one</root>', encoding='utf-8')
    f2.write_text('<root>two</root>', encoding='utf-8')

    resp = client.post('/resultaten/download-zip', json={'filenames': ['one.xml', 'two.xml']})
    assert resp.status_code == 200
    # Content should be a zip
    data = io.BytesIO(resp.data)
    with zipfile.ZipFile(data, 'r') as zf:
        names = zf.namelist()
        assert 'one.xml' in names
        assert 'two.xml' in names
        assert zf.read('one.xml').decode('utf-8') == '<root>one</root>'
        assert zf.read('two.xml').decode('utf-8') == '<root>two</root>'
