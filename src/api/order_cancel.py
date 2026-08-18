from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.schemas.order import OrderResponse
from src.services.order_service import OrderService


class CancelOrderRequest(BaseModel):
    reason: Optional[str] = None


router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    request: Optional[CancelOrderRequest] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = OrderService(db).cancel_order(str(user_id), order_id, request.reason if request else None)
    if result.get("code") == "ORDER_NOT_FOUND":
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"})
    if result.get("code") == "CANCEL_NOT_ALLOWED":
        raise HTTPException(
            status_code=409,
            detail={"code": "CANCEL_NOT_ALLOWED", "message": result["message"], "current_status": result["current_status"]},
        )
    return result["order"]
