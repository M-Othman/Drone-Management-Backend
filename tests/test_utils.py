from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app import store
from app.models import Drone, DroneStatus, Location, Order, OrderStatus
from app.utils import build_order_detail, estimate_eta_minutes

NOW = datetime.now(timezone.utc)
ORIGIN = Location(lat=25.2048, lng=55.2708)
DESTINATION = Location(lat=25.1972, lng=55.2744)
HANDOFF_LOCATION = Location(lat=25.2000, lng=55.2720)


def make_order(**kwargs) -> Order:
    defaults = dict(
        id=uuid4(),
        submitted_by="alice",
        status=OrderStatus.created,
        origin=ORIGIN,
        destination=DESTINATION,
        current_location=ORIGIN,
        created_at=NOW,
        updated_at=NOW,
    )
    return Order(**{**defaults, **kwargs})


def make_drone(**kwargs) -> Drone:
    defaults = dict(name="drone-1", status=DroneStatus.available, created_at=NOW)
    return Drone(**{**defaults, **kwargs})


# --- estimate_eta_minutes ---

def test_eta_same_location():
    loc = Location(lat=25.0, lng=55.0)
    assert estimate_eta_minutes(loc, loc) == 0.0


# --- build_order_detail ---

def test_detail_created_status():
    order = make_order(status=OrderStatus.created)
    detail = build_order_detail(order)
    assert detail.current_location == ORIGIN
    assert detail.eta_minutes is None


def test_detail_assigned_no_drone_location():
    drone = make_drone(location=None, current_order_id=None)
    store.drones[drone.name] = drone
    order = make_order(status=OrderStatus.assigned, assigned_drone_name=drone.name)
    detail = build_order_detail(order)
    assert detail.eta_minutes is None


def test_detail_delivered_status():
    order = make_order(status=OrderStatus.delivered, current_location=DESTINATION)
    detail = build_order_detail(order)
    assert detail.current_location == DESTINATION
    assert detail.eta_minutes is None


def test_detail_failed_status():
    order = make_order(status=OrderStatus.failed)
    detail = build_order_detail(order)
    assert detail.current_location == ORIGIN
    assert detail.eta_minutes is None
