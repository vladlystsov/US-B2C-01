from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.services.subscription_service import SubscriptionService


class SubscribeRequest(BaseModel):
    events: list[str] = Field(default_factory=lambda: ["BACK_IN_STOCK", "PRICE_DROP"])


router = APIRouter(prefix="/api/v1/favorites", tags=["Subscriptions"])


@router.post("/{product_id}/subscribe", status_code=204)
def subscribe(
    product_id: str,
    request: Optional[SubscribeRequest] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    events = (request.events if request else ["BACK_IN_STOCK", "PRICE_DROP"])
    try:
        result = SubscriptionService(db).subscribe(str(user_id), product_id, events)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(exc)})
    if result["status"] == "not_found":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found"})
    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail={"code": "SUBSCRIPTION_ALREADY_EXISTS", "message": "Subscription already exists"})
    if result["status"] == "b2b_error":
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})
    return Response(status_code=204)


@router.delete("/{product_id}/subscribe", status_code=204)
def unsubscribe(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    SubscriptionService(db).unsubscribe(str(user_id), product_id)
    return Response(status_code=204)
