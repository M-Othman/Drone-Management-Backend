from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app import store
from app.auth import require_role
from app.models import CurrentUser, Drone, DroneStatus, Order, OrderStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_drone_or_404(name: str) -> Drone:
    drone = store.drones.get(name)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone


def _get_order_or_404(order_id: UUID) -> Order:
    order = store.orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Job not found")
    return order


def _assert_assigned_to(order: Order, drone_name: str) -> None:
    if order.assigned_drone_name != drone_name:
        raise HTTPException(status_code=403, detail="This job is not assigned to you")


@router.get("/available", response_model=list[Order])
def list_available_jobs(
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    return [o for o in store.orders.values() if o.status == OrderStatus.created]


@router.post("/{order_id}/reserve", response_model=Order)
def reserve_job(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    if drone.status != DroneStatus.available:
        raise HTTPException(status_code=409, detail="Drone is not available")

    order = _get_order_or_404(order_id)
    if order.status != OrderStatus.created:
        raise HTTPException(status_code=409, detail="Job is not available")

    now = datetime.now(timezone.utc)
    store.orders[order_id] = order.model_copy(update={
        "status": OrderStatus.assigned,
        "assigned_drone_name": drone.name,
        "updated_at": now,
    })
    store.drones[drone.name] = drone.model_copy(update={
        "status": DroneStatus.assigned,
        "current_order_id": order_id,
    })
    return store.orders[order_id]


@router.post("/{order_id}/pickup", response_model=Order)
def pickup_job(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    order = _get_order_or_404(order_id)
    _assert_assigned_to(order, drone.name)

    if order.status != OrderStatus.assigned:
        raise HTTPException(status_code=409, detail="Order is not in assigned state")

    now = datetime.now(timezone.utc)
    store.orders[order_id] = order.model_copy(update={
        "status": OrderStatus.in_transit,
        "updated_at": now,
    })
    store.drones[drone.name] = drone.model_copy(update={"status": DroneStatus.in_transit})
    return store.orders[order_id]


@router.post("/{order_id}/deliver", response_model=Order)
def deliver_job(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    order = _get_order_or_404(order_id)
    _assert_assigned_to(order, drone.name)

    if order.status != OrderStatus.in_transit:
        raise HTTPException(status_code=409, detail="Order is not in transit")

    now = datetime.now(timezone.utc)
    store.orders[order_id] = order.model_copy(update={
        "status": OrderStatus.delivered,
        "current_location": order.destination,
        "updated_at": now,
    })
    store.drones[drone.name] = drone.model_copy(update={
        "status": DroneStatus.available,
        "current_order_id": None,
    })
    return store.orders[order_id]


@router.post("/{order_id}/fail", response_model=Order)
def fail_job(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    order = _get_order_or_404(order_id)
    _assert_assigned_to(order, drone.name)

    if order.status not in (OrderStatus.assigned, OrderStatus.in_transit):
        raise HTTPException(status_code=409, detail="Order cannot be failed in its current state")

    now = datetime.now(timezone.utc)
    store.orders[order_id] = order.model_copy(update={
        "status": OrderStatus.failed,
        "updated_at": now,
    })
    store.drones[drone.name] = drone.model_copy(update={
        "status": DroneStatus.available,
        "current_order_id": None,
    })
    return store.orders[order_id]
