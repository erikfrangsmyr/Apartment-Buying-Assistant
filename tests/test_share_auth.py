import pytest
from fastapi.testclient import TestClient

from app.main import create_app

TOKEN = "test-share-secret-token"


@pytest.fixture
def share_client(tmp_path):
    app = create_app(tmp_path / "share.db", share_token=TOKEN)
    with TestClient(app) as c:
        yield c


def test_health_unprotected_with_token(share_client):
    assert share_client.get("/health").status_code == 200


def test_app_forbidden_without_token(share_client):
    res = share_client.get("/app")
    assert res.status_code == 403


def test_app_ok_with_query_token(share_client):
    res = share_client.get(f"/app?token={TOKEN}")
    assert res.status_code == 200
    assert "Diligensvägen 4" in res.text


def test_app_ok_with_header_token(share_client):
    res = share_client.get("/app", headers={"X-Share-Token": TOKEN})
    assert res.status_code == 200


def test_static_forbidden_without_token(share_client):
    res = share_client.get("/static/css/style.css")
    assert res.status_code == 403


def test_static_ok_with_token(share_client):
    res = share_client.get(f"/static/css/style.css?token={TOKEN}")
    assert res.status_code == 200


def test_api_listings_open_without_token(share_client):
    res = share_client.get("/listings")
    assert res.status_code == 200


def test_no_token_middleware_unchanged(client):
    assert client.get("/app").status_code == 200


def test_cookie_allows_navigation_without_query_token(share_client):
    share_client.get(f"/app?token={TOKEN}")
    assert share_client.get("/app/jamfor").status_code == 200
    assert share_client.get("/static/css/style.css").status_code == 200
