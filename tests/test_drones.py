from uuid import UUID

from app import store
from tests.conftest import ORIGIN


# --- List drones ---

def test_admin_list_drones(client, make_headers, admin_token, drone_token):
    response = client.get("/drones/", headers=make_headers(admin_token))
    assert response.status_code == 200
    drones = response.json()
    assert len(drones) == 1
    assert drones[0]["name"] == "drone-1"
    assert drones[0]["status"] == "available"


def test_list_drones_requires_admin(client, make_headers, drone_token):
    response = client.get("/drones/", headers=make_headers(drone_token))
    assert response.status_code == 403


# --- Update location ---

def test_update_location(client, make_headers, drone_token):
    location = {"lat": 25.2040, "lng": 55.2700}
    response = client.patch("/drones/me/location", json=location, headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["location"] == location


def test_update_location_requires_drone(client, make_headers, enduser_token):
    response = client.patch("/drones/me/location", json={"lat": 25.0, "lng": 55.0}, headers=make_headers(enduser_token))
    assert response.status_code == 403


# --- Get current job ---

def test_get_current_job_no_job(client, make_headers, drone_token):
    response = client.get("/drones/me/job", headers=make_headers(drone_token))
    assert response.status_code == 404


def test_get_current_job(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.get("/drones/me/job", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


# --- Mark self broken ---

def test_mark_self_broken(client, make_headers, drone_token):
    response = client.post("/drones/me/broken", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "broken"


def test_mark_self_broken_already_broken(client, make_headers, drone_token):
    client.post("/drones/me/broken", headers=make_headers(drone_token))
    response = client.post("/drones/me/broken", headers=make_headers(drone_token))
    assert response.status_code == 409


def test_broken_with_assigned_order_resets_order(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post("/drones/me/broken", headers=make_headers(drone_token))
    stored_order = store.orders[UUID(order["id"])]
    assert stored_order.status == "created"
    assert stored_order.assigned_drone_name is None
    assert stored_order.current_location.model_dump() == ORIGIN


def test_broken_during_transit_updates_current_location(client, make_headers, drone_token, order):
    drone_location = {"lat": 25.2040, "lng": 55.2700}
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.patch("/drones/me/location", json=drone_location, headers=make_headers(drone_token))
    client.post("/drones/me/broken", headers=make_headers(drone_token))
    stored_order = store.orders[UUID(order["id"])]
    assert stored_order.status == "created"
    assert stored_order.current_location.model_dump() == drone_location
    assert stored_order.origin.model_dump() == ORIGIN


# --- Admin mark broken/fixed ---

def test_admin_mark_drone_broken(client, make_headers, admin_token, drone_token):
    response = client.patch("/drones/drone-1", json={"status": "broken"}, headers=make_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["status"] == "broken"


def test_admin_mark_drone_fixed(client, make_headers, admin_token, drone_token):
    client.patch("/drones/drone-1", json={"status": "broken"}, headers=make_headers(admin_token))
    response = client.patch("/drones/drone-1", json={"status": "available"}, headers=make_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["status"] == "available"


def test_admin_mark_drone_broken_already_broken(client, make_headers, admin_token, drone_token):
    client.patch("/drones/drone-1", json={"status": "broken"}, headers=make_headers(admin_token))
    response = client.patch("/drones/drone-1", json={"status": "broken"}, headers=make_headers(admin_token))
    assert response.status_code == 409


def test_admin_fix_non_broken_drone(client, make_headers, admin_token, drone_token):
    response = client.patch("/drones/drone-1", json={"status": "available"}, headers=make_headers(admin_token))
    assert response.status_code == 409


def test_admin_mark_nonexistent_drone(client, make_headers, admin_token):
    response = client.patch("/drones/ghost-drone", json={"status": "broken"}, headers=make_headers(admin_token))
    assert response.status_code == 404


def test_admin_broken_triggers_handoff(client, make_headers, admin_token, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.patch("/drones/drone-1", json={"status": "broken"}, headers=make_headers(admin_token))
    stored_order = store.orders[UUID(order["id"])]
    assert stored_order.status == "created"
    assert stored_order.assigned_drone_name is None
