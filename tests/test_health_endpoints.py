from fastapi.testclient import TestClient

from app.database.database import get_db
from app.main import app


def test_health_returns_api_liveness(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "loom-api",
    }


def test_live_alias_returns_api_liveness(client: TestClient):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_database_health_checks_minimal_database_query(client: TestClient):
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": "ok"},
    }


def test_readiness_combines_api_and_database_health(client: TestClient):
    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {
            "api": "ok",
            "database": "ok",
        },
    }


def test_database_health_returns_503_when_database_check_fails():
    class BrokenSession:
        def execute(self, _statement):
            raise RuntimeError("database unavailable")

    def override_get_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            response = test_client.get("/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "unhealthy",
            "checks": {"database": "unhealthy"},
        }
    }
