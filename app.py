
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

app = FastAPI()

deliveries = {}
next_id = 1

VALID_STATUSES = ["created", "in_transit", "delivered"]


class DeliveryCreate(BaseModel):
    recipient: str
    address: str


class StatusUpdate(BaseModel):
    status: str


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
):
    return JSONResponse(
        status_code=400,
        content={"error": "Invalid request"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/deliveries", status_code=201)
def create_delivery(data: DeliveryCreate):
    global next_id

    if not data.recipient.strip():
        raise HTTPException(400, "Recipient cannot be empty")

    if not data.address.strip():
        raise HTTPException(400, "Address cannot be empty")

    delivery = {
        "id": next_id,
        "recipient": data.recipient,
        "address": data.address,
        "status": "created",
    }

    deliveries[next_id] = delivery
    next_id += 1

    return delivery


@app.get("/deliveries")
def list_deliveries(status: Optional[str] = None):
    if status is not None and status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")

    result = list(deliveries.values())

    if status is not None:
        result = [
            delivery
            for delivery in result
            if delivery["status"] == status
        ]

    return result


@app.get("/deliveries/{delivery_id}")
def get_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    return deliveries[delivery_id]


@app.patch("/deliveries/{delivery_id}/status")
def update_status(delivery_id: int, data: StatusUpdate):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    if data.status not in VALID_STATUSES:
        raise HTTPException(400, "Invalid status")

    delivery = deliveries[delivery_id]
    current_status = delivery["status"]

    current_index = VALID_STATUSES.index(current_status)
    new_index = VALID_STATUSES.index(data.status)

    if new_index != current_index + 1:
        raise HTTPException(409, "Invalid status transition")

    delivery["status"] = data.status

    return delivery


@app.delete("/deliveries/{delivery_id}")
def delete_delivery(delivery_id: int):
    if delivery_id not in deliveries:
        raise HTTPException(404, "Delivery not found")

    if deliveries[delivery_id]["status"] != "created":
        raise HTTPException(
            409, "Only created deliveries can be deleted"
        )

    del deliveries[delivery_id]

    return Response(status_code=204)
