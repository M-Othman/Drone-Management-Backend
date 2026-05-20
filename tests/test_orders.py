from tests.conftest import DESTINATION, ORIGIN


# --- Create order ---

def test_create_order(client, make_headers, enduser_token):
    response = client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=make_headers(enduser_token))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "created"
    assert data["origin"] == ORIGIN
    assert data["destination"] == DESTINATION
    assert data["current_location"] == ORIGIN
    assert data["submitted_by"] == "alice"


def test_create_order_requires_enduser(client, make_headers, admin_token):
    response = client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=make_headers(admin_token))
    assert response.status_code == 403


# --- Get order ---

def test_get_own_order(client, make_headers, enduser_token, order):
    response = client.get(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


def test_get_order_includes_eta_and_location(client, make_headers, enduser_token, order):
    response = client.get(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    data = response.json()
    assert "current_location" in data
    assert "eta_minutes" in data


def test_enduser_cannot_get_another_users_order(client, make_headers, order):
    other_token = client.post("/auth/token", json={"name": "bob", "type": "enduser"}).json()["access_token"]
    response = client.get(f"/orders/{order['id']}", headers=make_headers(other_token))
    assert response.status_code == 404


def test_admin_can_get_any_order(client, make_headers, admin_token, order):
    response = client.get(f"/orders/{order['id']}", headers=make_headers(admin_token))
    assert response.status_code == 200


def test_get_nonexistent_order(client, make_headers, enduser_token):
    response = client.get("/orders/00000000-0000-0000-0000-000000000000", headers=make_headers(enduser_token))
    assert response.status_code == 404


# --- List orders ---

def test_admin_list_orders(client, make_headers, admin_token, order):
    response = client.get("/orders/", headers=make_headers(admin_token))
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["id"] == order["id"]
    assert orders[0]["status"] == "created"


def test_admin_list_orders_by_ids(client, make_headers, admin_token, enduser_token):
    o1 = client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=make_headers(enduser_token)).json()
    o2 = client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=make_headers(enduser_token)).json()
    client.post("/orders/", json={"origin": ORIGIN, "destination": DESTINATION}, headers=make_headers(enduser_token))
    response = client.get(f"/orders/?ids={o1['id']}&ids={o2['id']}", headers=make_headers(admin_token))
    assert response.status_code == 200
    returned_ids = {o["id"] for o in response.json()}
    assert returned_ids == {o1["id"], o2["id"]}


def test_admin_list_orders_by_ids_ignores_unknown(client, make_headers, admin_token, order):
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/orders/?ids={order['id']}&ids={fake_id}", headers=make_headers(admin_token))
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == order["id"]


# --- Update order ---

def test_admin_update_destination(client, make_headers, admin_token, order):
    new_dest = {"lat": 25.1900, "lng": 55.2600}
    response = client.patch(f"/orders/{order['id']}", json={"destination": new_dest}, headers=make_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["destination"] == new_dest
    assert response.json()["origin"] == ORIGIN


def test_admin_update_origin(client, make_headers, admin_token, order):
    new_origin = {"lat": 25.2100, "lng": 55.2800}
    response = client.patch(f"/orders/{order['id']}", json={"origin": new_origin}, headers=make_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["origin"] == new_origin
    assert response.json()["destination"] == DESTINATION


def test_cannot_update_delivered_order(client, make_headers, admin_token, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/deliver", headers=make_headers(drone_token))
    response = client.patch(f"/orders/{order['id']}", json={"destination": DESTINATION}, headers=make_headers(admin_token))
    assert response.status_code == 409


def test_update_requires_admin(client, make_headers, enduser_token, order):
    response = client.patch(f"/orders/{order['id']}", json={"destination": DESTINATION}, headers=make_headers(enduser_token))
    assert response.status_code == 403


# --- Cancel order ---

def test_cancel_created_order(client, make_headers, enduser_token, order):
    response = client.delete(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    assert response.status_code == 204


def test_cancel_assigned_order(client, make_headers, enduser_token, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.delete(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    assert response.status_code == 204


def test_cancel_frees_drone(client, make_headers, enduser_token, drone_token, order):
    from app import store
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.delete(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    assert store.drones["drone-1"].status == "available"
    assert store.drones["drone-1"].current_order_id is None


def test_cannot_cancel_in_transit_order(client, make_headers, enduser_token, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    response = client.delete(f"/orders/{order['id']}", headers=make_headers(enduser_token))
    assert response.status_code == 409


def test_enduser_cannot_cancel_other_user_order(client, make_headers, order):
    other_token = client.post("/auth/token", json={"name": "bob", "type": "enduser"}).json()["access_token"]
    response = client.delete(f"/orders/{order['id']}", headers=make_headers(other_token))
    assert response.status_code == 404
