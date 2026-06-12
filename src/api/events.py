from fastapi import APIRouter, Depends, HTTPException, Header
from src.schemas.event import ProductEventRequest
from src.services.event_service import EventService
from src.database import get_db
from src.config import settings
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter(prefix="/api/v1/events", tags=["Events"])


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2B_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-Service-Key"}
        )
    return True


@router.post("/product")
def handle_product_event(
    payload: ProductEventRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key)
):
    service = EventService(db)
    result = service.handle_product_event(payload.model_dump())

    if result["status"] == "duplicate":
        return {"accepted": True}

    return {"accepted": True}
