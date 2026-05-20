from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app import store
from app.auth import require_role
from app.models import (
    CurrentUser,
    Drone,
    DroneStatus,
    Location,
    OrderDetailResponse,
    UpdateDroneStatusRequest,
)
from app.utils import build_order_detail, handle_drone_broken

router = APIRouter(prefix="/drones", tags=["drones"])


def _get_drone_or_404(name: str) -> Drone:
    drone = store.drones.get(name)
    if not drone:
        raise HTTPException(status_code=404, detail="Drone not found")
    return drone


# --- Drone self-management (must be defined before /{drone_name}) ---

@router.post("/me/broken", response_model=Drone)
def mark_self_broken(
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    if drone.status == DroneStatus.broken:
        raise HTTPException(status_code=409, detail="Drone is already broken")
    handle_drone_broken(drone)
    return store.drones[user.name]


@router.patch("/me/location", response_model=Drone)
def update_location(
    body: Location,
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    updated = drone.model_copy(update={"location": body})
    store.drones[user.name] = updated
    return updated


@router.get("/me/job", response_model=OrderDetailResponse)
def get_current_job(
    user: Annotated[CurrentUser, Depends(require_role("drone"))],
):
    drone = _get_drone_or_404(user.name)
    if not drone.current_order_id:
        raise HTTPException(status_code=404, detail="No active job")
    order = store.orders.get(drone.current_order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return build_order_detail(order)


# --- Admin drone management ---

@router.get("/", response_model=list[Drone])
def list_drones(
    user: Annotated[CurrentUser, Depends(require_role("admin"))],
):
    return list(store.drones.values())


@router.patch("/{drone_name}", response_model=Drone)
def update_drone_status(
    drone_name: str,
    body: UpdateDroneStatusRequest,
    user: Annotated[CurrentUser, Depends(require_role("admin"))],
):
    drone = _get_drone_or_404(drone_name)

    if body.status == "broken":
        if drone.status == DroneStatus.broken:
            raise HTTPException(status_code=409, detail="Drone is already broken")
        handle_drone_broken(drone)
        return store.drones[drone_name]

    if drone.status != DroneStatus.broken:
        raise HTTPException(status_code=409, detail="Drone is not broken")
    updated = drone.model_copy(update={"status": DroneStatus.available})
    store.drones[drone_name] = updated
    return updated
