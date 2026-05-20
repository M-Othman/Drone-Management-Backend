from app import store


def test_get_token_admin(client):
    response = client.post("/auth/token", json={"name": "alice", "type": "admin"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()


def test_get_token_enduser(client):
    response = client.post("/auth/token", json={"name": "alice", "type": "enduser"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_get_token_drone(client):
    response = client.post("/auth/token", json={"name": "drone-1", "type": "drone"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_drone_auto_registered_on_token(client):
    assert "drone-1" not in store.drones
    client.post("/auth/token", json={"name": "drone-1", "type": "drone"})
    assert "drone-1" in store.drones


def test_drone_not_duplicated_on_repeat_token(client):
    client.post("/auth/token", json={"name": "drone-1", "type": "drone"})
    client.post("/auth/token", json={"name": "drone-1", "type": "drone"})
    assert len(store.drones) == 1


def test_invalid_role_rejected(client):
    response = client.post("/auth/token", json={"name": "alice", "type": "hacker"})
    assert response.status_code == 422


def test_missing_name_rejected(client):
    response = client.post("/auth/token", json={"type": "admin"})
    assert response.status_code == 422


def test_protected_endpoint_rejects_no_token(client):
    response = client.get("/orders/")
    assert response.status_code == 401


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get("/orders/", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_enduser_get_orders_rejected(client, enduser_token):
    response = client.get("/orders/", headers={"Authorization": f"Bearer {enduser_token}"})
    assert response.status_code == 403
