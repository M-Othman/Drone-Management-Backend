import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app

ORIGIN = {"lat": 25.2048, "lng": 55.2708}
DESTINATION = {"lat": 25.1972, "lng": 55.2744}


@pytest.fixture(autouse=True)
def reset_store():
    store.drones.clear()
    store.orders.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_token(client):
    return client.post("/auth/token", json={"name": "admin", "type": "admin"}).json()["access_token"]


@pytest.fixture
def enduser_token(client):
    return client.post("/auth/token", json={"name": "alice", "type": "enduser"}).json()["access_token"]


@pytest.fixture
def drone_token(client):
    return client.post("/auth/token", json={"name": "drone-1", "type": "drone"}).json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def enduser_headers(enduser_token):
    return {"Authorization": f"Bearer {enduser_token}"}


@pytest.fixture
def drone_headers(drone_token):
    return {"Authorization": f"Bearer {drone_token}"}


@pytest.fixture
def order(client, enduser_headers):
    response = client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=enduser_headers)
    return response.json()
