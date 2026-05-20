from fastapi import FastAPI
from dotenv import load_dotenv

from app.routers import auth, drones, jobs, orders

load_dotenv()

app = FastAPI(title="Drone Delivery Management API")

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(drones.router)
app.include_router(jobs.router)

@app.get("/health")
def health():
    return {"status": "ok"}
