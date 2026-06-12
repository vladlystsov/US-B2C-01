from fastapi import APIRouter, Depends, HTTPException
from src.services.subscription_service import SubscriptionService, VALID_NOTIFY_ON
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List


class SubscribeRequest(BaseModel):
    notify_on: List[str]


router = APIRouter(prefix="/api/v1/favorites", tags=["Subscriptions"])


@router.post("/{product_id}/subscribe")
def subscribe(
    product_id: str,
    request: SubscribeRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = SubscriptionService(db)

    try:
        result = service.subscribe(str(user_id), product_id, request.notify_on)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": str(e)})

    if result["status"] == "duplicate":
        raise HTTPException(status_code=409, detail={"code": "SUBSCRIPTION_ALREADY_EXISTS", "message": "Subscription already exists"})

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=201, content=result)


@router.delete("/{product_id}/subscribe", status_code=204)
def unsubscribe(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = SubscriptionService(db)
    service.unsubscribe(str(user_id), product_id)
    return None
