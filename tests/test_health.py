"""Health-check endpoint tests."""

import app as app_module
import inventory.core as core_module


def test_health_returns_ok_json_without_login(client, users):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_check_fails(client, monkeypatch):
    def broken_get_db():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(app_module, "get_db", broken_get_db)
    monkeypatch.setattr(core_module, "get_db", broken_get_db)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.is_json
    assert response.get_json() == {"status": "error", "database": "error"}
