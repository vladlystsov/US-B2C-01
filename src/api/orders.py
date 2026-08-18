from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.schemas.order import OrderCreateRequest, OrderResponse
from src.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    result = OrderService(db).create_order(str(user_id), request, idempotency_key)
    if result.get("code") == "CART_INVALID":
        raise HTTPException(
            status_code=422,
            detail={"is_valid": False, "cart": result["cart"], "issues": result["issues"]},
        )
    if result.get("code") == "B2B_UNAVAILABLE":
        raise HTTPException(status_code=503, detail={"code": result["code"], "message": result["message"]})
    if result.get("code") == "RESERVE_FAILED":
        raise HTTPException(
            status_code=409,
            detail={"code": result["code"], "message": result["message"], "failed_items": result.get("failed_items", [])},
        )
    return result["order"]


@router.get("")
def get_orders(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
):
    return OrderService(db).get_orders(str(user_id), limit=limit, offset=offset, status=status)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    result = OrderService(db).get_order(str(user_id), order_id)
    if not result:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"})
    return result
