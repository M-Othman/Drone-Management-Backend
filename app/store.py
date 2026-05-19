from typing import Dict
from uuid import UUID

from app.models import Drone, Order

drones: Dict[str, Drone] = {}  
orders: Dict[UUID, Order] = {} 
