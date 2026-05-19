from fastapi import FastAPI
from dotenv import load_dotenv

from app.routers import auth, orders

load_dotenv()

app = FastAPI(title="Drone Delivery Management API")

app.include_router(auth.router)
app.include_router(orders.router)

@app.get("/health")
def health():
    return {"status": "ok"}
