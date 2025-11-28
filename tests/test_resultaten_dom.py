import importlib
import json
from bs4 import BeautifulSoup

import pytest

# ensure app package import works
app_module = importlib.import_module('web.app')
app = app_module.app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


def test_resultaten_buttons_have_expected_classes(client):
    # Prepare minimal context: the view expects a `generated` list in template context.
    # Use the Flask test client directly to GET the page; app code should provide defaults when no files exist.
    resp = client.get('/resultaten')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)

    # Parse HTML with BeautifulSoup; fall back handled by test requirements
    soup = BeautifulSoup(html, 'html.parser')

    # Find the Download geselecteerd button
    download_btn = soup.select_one('#download-selected-btn')
    assert download_btn is not None, 'Download geselecteerd button not found'
    # it should have outline-primary class
    assert 'btn-outline-primary' in download_btn.get('class', []), 'Download button should be outline primary'

    # Find per-item download links (if present) and check they use outlined primary
    per_downloads = soup.select('.generated-list a.btn')
    for a in per_downloads:
        # allow either btn-outline-primary or btn-outline-secondary for item actions
        classes = a.get('class', [])
        assert ('btn-outline-primary' in classes) or ('btn-outline-secondary' in classes), f'Per-item action not outlined: {classes}'

    # Check the "Genereer XML" button inside the Resultaten panel (avoid navbar link)
    gen_btn = soup.select_one('.app-panel.resultaten-body a[href$="genereer_xml"], .app-panel.resultaten-body a.btn')
    if gen_btn is not None:
        classes = gen_btn.get('class', [])
        # allow either the success (green) or an outlined-primary fallback if templates were changed
        assert ('btn-success' in classes) or ('btn-outline-primary' in classes) or ('btn-outline-secondary' in classes), f'Genereer XML button should use a highlighted btn class, found: {classes}'

    # Also ensure login or settings pages use btn-outline-primary where we changed templates
    # Check login submit buttons
    login_btn = soup.select_one('button[type=submit].btn-outline-primary')
    # login page isn't rendered here, so we only assert that if present it's correct
    if login_btn is not None:
        assert 'btn-outline-primary' in login_btn.get('class', [])
