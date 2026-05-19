from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lng: float


class DroneStatus(str, Enum):
    available = "available"
    assigned = "assigned"
    in_transit = "in_transit"
    broken = "broken"


class OrderStatus(str, Enum):
    created = "created"
    assigned = "assigned"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


class Drone(BaseModel):
    name: str
    status: DroneStatus = DroneStatus.available
    location: Optional[Location] = None
    current_order_id: Optional[UUID] = None
    created_at: datetime


class Order(BaseModel):
    id: UUID
    submitted_by: str
    status: OrderStatus = OrderStatus.created
    origin: Location
    destination: Location
    assigned_drone_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Auth
class TokenRequest(BaseModel):
    name: str
    type: Literal["admin", "enduser", "drone"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    name: str
    role: Literal["admin", "enduser", "drone"]


# Orders
class CreateOrderRequest(BaseModel):
    origin: Location
    destination: Location


class UpdateOrderRequest(BaseModel):
    origin: Optional[Location] = None
    destination: Optional[Location] = None


class OrderDetailResponse(BaseModel):
    id: UUID
    submitted_by: str
    status: OrderStatus
    origin: Location
    destination: Location
    assigned_drone_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    drone_location: Optional[Location] = None
    eta_minutes: Optional[float] = None
