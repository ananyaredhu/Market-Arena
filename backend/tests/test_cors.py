"""CORS permits both local frontend development origins."""
import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


@pytest.mark.parametrize("origin", ["http://localhost:3000", "http://localhost:3001"])
def test_local_frontend_preflight_is_allowed(origin):
    response = client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
