from fastapi.testclient import TestClient

from main import app


def test_api_responses_include_browser_security_and_no_store_headers(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    response = TestClient(app).get("/api/auth/config")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers


def test_production_responses_include_hsts(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_production_cookie_authenticated_write_requires_same_origin(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_BASE_URL", "https://adjudication.example.test")
    client = TestClient(app)
    payload = {"email": "nobody@example.test", "password": "invalid"}
    denied = client.post(
        "/api/auth/login",
        json=payload,
        cookies={"acrn_demo_session": "attacker-supplied-cookie"},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Cross-site state-changing request denied."

    same_origin = client.post(
        "/api/auth/login",
        json=payload,
        cookies={"acrn_demo_session": "attacker-supplied-cookie"},
        headers={"Origin": "https://adjudication.example.test"},
    )
    assert same_origin.status_code == 401
