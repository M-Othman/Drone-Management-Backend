from datetime import datetime, timezone

from app import store
from app.models import Drone, DroneStatus, Location, Order, OrderDetailResponse, OrderStatus

DRONE_SPEED_KMH = 50
ETA_BUFFER = 1.15


def estimate_eta_minutes(loc1: Location, loc2: Location) -> float:
    dlat = (loc2.lat - loc1.lat) * 111
    dlng = (loc2.lng - loc1.lng) * 111
    distance_km = (dlat ** 2 + dlng ** 2) ** 0.5
    return (distance_km / DRONE_SPEED_KMH) * ETA_BUFFER * 60


def build_order_detail(order: Order) -> OrderDetailResponse:
    current_location = order.current_location
    eta_minutes = None

    if order.status == OrderStatus.assigned:
        drone = store.drones.get(order.assigned_drone_name)
        if drone and drone.location:
            eta_minutes = estimate_eta_minutes(drone.location, order.origin) + \
                          estimate_eta_minutes(order.origin, order.destination)
    elif order.status == OrderStatus.in_transit:
        drone = store.drones.get(order.assigned_drone_name)
        if drone and drone.location:
            current_location = drone.location
            eta_minutes = estimate_eta_minutes(drone.location, order.destination)

    return OrderDetailResponse(
        **order.model_dump(exclude={"current_location"}),
        current_location=current_location,
        eta_minutes=eta_minutes,
    )


def handle_drone_broken(drone: Drone) -> None:
    now = datetime.now(timezone.utc)
    if drone.current_order_id:
        order = store.orders.get(drone.current_order_id)
        if order and order.status in (OrderStatus.assigned, OrderStatus.in_transit):
            store.orders[order.id] = order.model_copy(update={
                "status": OrderStatus.created,
                "assigned_drone_name": None,
                "current_location": drone.location if order.status == OrderStatus.in_transit and drone.location else order.current_location,
                "updated_at": now,
            })

    store.drones[drone.name] = drone.model_copy(update={
        "status": DroneStatus.broken,
        "current_order_id": None,
    })
