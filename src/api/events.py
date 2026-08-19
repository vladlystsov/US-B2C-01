from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.schemas.event import B2BEventRequest
from src.services.event_service import EventService

router = APIRouter(prefix="/api/v1/b2b", tags=["B2B Events"])


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2B_TO_B2C_KEY:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-Service-Key"})


@router.post("/events", status_code=202)
def handle_b2b_event(
    payload: B2BEventRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_service_key),
):
    result = EventService(db).handle_b2b_event(payload.model_dump(mode="json"))
    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail={"code": "DUPLICATE_EVENT", "message": "Event already processed"})
    return Response(status_code=202)
