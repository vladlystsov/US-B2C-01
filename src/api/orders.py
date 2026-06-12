from fastapi import APIRouter, Depends, HTTPException, Header, Query
from src.schemas.order import OrderCreateRequest, OrderResponse
from src.services.order_service import OrderService
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    result = service.create_order(
        user_id=str(user_id),
        items=[item.model_dump() for item in request.items],
        idempotency_key=request.idempotency_key,
        delivery_address=request.delivery_address
    )

    if result.get("code") == "INVALID_REQUEST":
        raise HTTPException(status_code=400, detail={"code": result["code"], "message": result["message"]})

    if result.get("code") == "B2B_UNAVAILABLE":
        raise HTTPException(status_code=503, detail={"code": result["code"], "message": result["message"]})

    if result.get("code") == "RESERVE_FAILED":
        raise HTTPException(status_code=409, detail={
            "code": result["code"],
            "message": result["message"],
            "failed_items": result.get("failed_items", [])
        })

    if result["status"] == "existing":
        return result["order"]

    return result["order"]


@router.get("/", response_model=dict)
def get_orders(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None
):
    service = OrderService(db)
    return service.get_orders(str(user_id), limit=limit, offset=offset, status=status)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    result = service.get_order(str(user_id), order_id)

    if not result:
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"})

    return result
