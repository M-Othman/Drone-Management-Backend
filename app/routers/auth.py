from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app import store
from app.auth import create_token
from app.models import Drone, DroneStatus, TokenRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/token", response_model=TokenResponse)
def get_token(body: TokenRequest):
    if body.type == "drone" and body.name not in store.drones:
        store.drones[body.name] = Drone(
            name=body.name,
            status=DroneStatus.available,
            created_at=datetime.now(timezone.utc),
        )

    return TokenResponse(access_token=create_token(body.name, body.type))
