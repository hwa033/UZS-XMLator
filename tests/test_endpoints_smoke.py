import pytest

from web import app


@pytest.fixture
def client():
    app.testing = True
    with app.test_client() as client:
        yield client


def test_index(client):
    rv = client.get("/")
    assert rv.status_code in (200, 302)


def test_genereer_json(client):
    rv = client.get("/genereer_json")
    assert rv.status_code in (200, 302, 404)


def test_genereer_xml(client):
    rv = client.get("/genereer_xml")
    assert rv.status_code in (200, 302, 404)


def test_download_not_found(client):
    rv = client.get("/download/nonexistent.file")
    # either redirect back to generate page or 404
    assert rv.status_code in (302, 404)
