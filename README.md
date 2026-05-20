# Drone Management Backend

This project is a small backend service for orders to be placed in order to be delivered by drones. 

## Requirements

### Drones

Drones can:
1. Reserve a job
2. Notify they have acquired a job's goods
3. Notify of delivery success or failure
4. Notify they are broken
5. Update their current location (lat/lng)
6. Request for their current job details (if assigned)

### End-users

End-users can:
1. Submit a job (origin + destination)
2. Withdraw orders that have yet to be picked up
3. Get details on orders (status, eta, location)

### Admins

Admins can:
1. Get multiple orders in bulk
2. Change origin/destination of orders
3. Get a list of drones
4. Mark a drone as broken/fixed

## Setup

### Create python env

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Install requirements

```bash
pip install -r requirements.txt
```

### Run tests

```bash
pytest
```

### Start server

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`.

## Auth

All endpoints require a Bearer JWT. Obtain one via:

```
POST /auth/token
{ "name": "alice", "type": "admin" }
```

Type can be admin, enduser, or drone.
Some APIs can only be accessed by a certain type.

Pass the returned token as `Authorization: Bearer <token>` on all subsequent requests.

