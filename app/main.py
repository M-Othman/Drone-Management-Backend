from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv

from app.routers import auth, drones, jobs, orders

load_dotenv()

app = FastAPI(title="Drone Delivery Management API")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version="1.0.0", routes=app.routes)
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer"}
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(drones.router)
app.include_router(jobs.router)

@app.get("/health")
def health():
    return {"status": "ok"}
