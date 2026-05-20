from uuid import UUID

from app import store
from tests.conftest import ORIGIN


# --- List available jobs ---

def test_list_available_jobs(client, make_headers, drone_token, order):
    response = client.get("/jobs/available", headers=make_headers(drone_token))
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == order["id"]


def test_list_available_jobs_excludes_assigned(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.get("/jobs/available", headers=make_headers(drone_token))
    assert response.json() == []


def test_list_available_jobs_requires_drone(client, make_headers, enduser_token, order):
    response = client.get("/jobs/available", headers=make_headers(enduser_token))
    assert response.status_code == 403


# --- Reserve ---

def test_reserve_job(client, make_headers, drone_token, order):
    response = client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "assigned"
    assert response.json()["assigned_drone_name"] == "drone-1"


def test_reserve_updates_drone_status(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    assert store.drones["drone-1"].status == "assigned"
    assert store.drones["drone-1"].current_order_id == UUID(order["id"])


def test_reserve_unavailable_drone_rejected(client, make_headers, drone_token, order):
    second_order = client.post("/orders/", json={"origin": ORIGIN, "destination": {"lat": 25.19, "lng": 55.27}},
                               headers=make_headers(client.post("/auth/token", json={"name": "bob", "type": "enduser"}).json()["access_token"])).json()
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{second_order['id']}/reserve", headers=make_headers(drone_token))
    assert response.status_code == 409


def test_reserve_already_assigned_job_rejected(client, make_headers, drone_token, order):
    other_drone_token = client.post("/auth/token", json={"name": "drone-2", "type": "drone"}).json()["access_token"]
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(other_drone_token))
    assert response.status_code == 409


def test_reserve_nonexistent_job(client, make_headers, drone_token):
    response = client.post("/jobs/00000000-0000-0000-0000-000000000000/reserve", headers=make_headers(drone_token))
    assert response.status_code == 404


# --- Pickup ---

def test_pickup_job(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "in_transit"


def test_pickup_updates_drone_status(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    assert store.drones["drone-1"].status == "in_transit"


def test_pickup_wrong_drone_rejected(client, make_headers, drone_token, order):
    other_drone_token = client.post("/auth/token", json={"name": "drone-2", "type": "drone"}).json()["access_token"]
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(other_drone_token))
    assert response.status_code == 403


def test_pickup_not_assigned_rejected(client, make_headers, drone_token, order):
    response = client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    assert response.status_code == 403


# --- Deliver ---

def test_deliver_job(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/deliver", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "delivered"


def test_deliver_frees_drone(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/deliver", headers=make_headers(drone_token))
    assert store.drones["drone-1"].status == "available"
    assert store.drones["drone-1"].current_order_id is None


def test_deliver_updates_current_location(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/deliver", headers=make_headers(drone_token))
    stored_order = store.orders[UUID(order["id"])]
    assert stored_order.current_location == stored_order.destination


def test_deliver_not_in_transit_rejected(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/deliver", headers=make_headers(drone_token))
    assert response.status_code == 409


# --- Fail ---

def test_fail_job_in_transit(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/fail", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_fail_job_assigned(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    response = client.post(f"/jobs/{order['id']}/fail", headers=make_headers(drone_token))
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_fail_frees_drone(client, make_headers, drone_token, order):
    client.post(f"/jobs/{order['id']}/reserve", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/pickup", headers=make_headers(drone_token))
    client.post(f"/jobs/{order['id']}/fail", headers=make_headers(drone_token))
    assert store.drones["drone-1"].status == "available"
    assert store.drones["drone-1"].current_order_id is None


def test_fail_not_assigned_rejected(client, make_headers, drone_token, order):
    response = client.post(f"/jobs/{order['id']}/fail", headers=make_headers(drone_token))
    assert response.status_code == 403
