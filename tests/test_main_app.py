from fastapi.testclient import TestClient
# It's important to adjust the import path based on the project structure
# Assuming pytest is run from the root of the project.
from infra.docker.app.app.main import app

client = TestClient(app)

def test_health_check():
    """
    Tests the /healthz endpoint.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root():
    """
    Tests the root (/) endpoint.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Axity Infra Ops Lab"}
