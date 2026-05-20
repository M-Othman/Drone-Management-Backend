from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app import store
from app.auth import require_role
from app.models import (
    CreateOrderRequest,
    CurrentUser,
    Order,
    OrderDetailResponse,
    OrderStatus,
    UpdateOrderRequest,
)
from app.utils import build_order_detail

router = APIRouter(prefix="/orders", tags=["orders"])

CANCELLABLE_STATES = {OrderStatus.created, OrderStatus.assigned}
TERMINAL_STATES = {OrderStatus.delivered, OrderStatus.failed, OrderStatus.cancelled}


def _get_order_or_404(order_id: UUID, user: CurrentUser) -> Order:
    order = store.orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if user.role == "enduser" and order.submitted_by != user.name:
        # Return 404 rather than 403 to avoid confirming the order exists
        raise HTTPException(status_code=404, detail="Order not found")
    return order



@router.post("/", response_model=Order)
def create_order(
    body: CreateOrderRequest,
    user: Annotated[CurrentUser, Depends(require_role("enduser"))],
):
    now = datetime.now(timezone.utc)
    order = Order(
        id=uuid4(),
        submitted_by=user.name,
        origin=body.origin,
        destination=body.destination,
        current_location=body.origin,
        created_at=now,
        updated_at=now,
    )
    store.orders[order.id] = order
    return order


@router.get("/", response_model=list[Order])
def list_orders(
    user: Annotated[CurrentUser, Depends(require_role("admin"))],
    ids: Annotated[list[UUID] | None, Query()] = None,
):
    if ids:
        return [store.orders[i] for i in ids if i in store.orders]
    return list(store.orders.values())


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("enduser", "admin"))],
):
    return build_order_detail(_get_order_or_404(order_id, user))


@router.patch("/{order_id}", response_model=Order)
def update_order(
    order_id: UUID,
    body: UpdateOrderRequest,
    user: Annotated[CurrentUser, Depends(require_role("admin"))],
):
    order = _get_order_or_404(order_id, user)
    if order.status in TERMINAL_STATES:
        raise HTTPException(status_code=409, detail="Cannot modify a completed or cancelled order")
    updated = order.model_copy(update={
        "origin": body.origin or order.origin,
        "destination": body.destination or order.destination,
        "updated_at": datetime.now(timezone.utc),
    })
    store.orders[order_id] = updated
    return updated


@router.delete("/{order_id}", status_code=204)
def cancel_order(
    order_id: UUID,
    user: Annotated[CurrentUser, Depends(require_role("enduser"))],
):
    order = _get_order_or_404(order_id, user)
    if order.status not in CANCELLABLE_STATES:
        raise HTTPException(status_code=409, detail="Order cannot be cancelled once picked up")
    now = datetime.now(timezone.utc)
    store.orders[order_id] = order.model_copy(update={
        "status": OrderStatus.cancelled,
        "updated_at": now,
    })
    if order.assigned_drone_name:
        drone = store.drones.get(order.assigned_drone_name)
        if drone:
            store.drones[drone.name] = drone.model_copy(update={
                "status": "available",
                "current_order_id": None,
            })
