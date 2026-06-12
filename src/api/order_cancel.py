from fastapi import APIRouter, Depends, HTTPException
from src.schemas.order import OrderResponse
from src.services.order_service import OrderService
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from sqlalchemy.orm import Session


router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = OrderService(db)
    result = service.cancel_order(str(user_id), order_id)

    if result.get("code") == "ORDER_NOT_FOUND":
        raise HTTPException(status_code=404, detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"})

    if result.get("code") == "CANCEL_NOT_ALLOWED":
        raise HTTPException(status_code=409, detail={
            "code": "CANCEL_NOT_ALLOWED",
            "message": f"Отмена невозможна: заказ в статусе {result['current_status']}",
            "current_status": result["current_status"]
        })

    return result["order"]
