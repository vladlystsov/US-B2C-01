from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from jose import jwt
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.schemas.cart import AddToCartRequest, CartResponse, UpdateCartItemRequest
from src.services.cart_service import CartService

router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])


def get_identity(x_session_id: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        try:
            user_id = jwt.decode(
                authorization.split(" ", 1)[1], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            ).get("sub")
        except Exception:
            pass
    if user_id:
        return {"user_id": user_id, "session_id": None}
    if x_session_id:
        return {"user_id": None, "session_id": x_session_id}
    raise HTTPException(status_code=400, detail={"code": "MISSING_CART_IDENTITY", "message": "Provide Authorization header or X-Session-Id"})


@router.get("", response_model=CartResponse)
def get_cart(identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    return CartService(db).get_cart(**identity)


@router.post("/items", response_model=CartResponse)
def add_to_cart(request: AddToCartRequest, identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    return CartService(db).add_item(request.sku_id, request.quantity, **identity)


@router.patch("/items/{sku_id}", response_model=CartResponse)
def update_cart_item(
    sku_id: str,
    request: UpdateCartItemRequest,
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db),
):
    result = CartService(db).update_item(sku_id, request.quantity, **identity)
    if result.get("error") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Cart item not found"})
    return result


@router.delete("/items/{sku_id}", response_model=CartResponse)
def remove_from_cart(sku_id: str, identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    result = CartService(db).remove_item(sku_id, **identity)
    if result.get("error") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Cart item not found"})
    return result


@router.delete("", status_code=204)
def clear_cart(identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    CartService(db).clear_cart(**identity)
    return Response(status_code=204)


@router.post("/merge", response_model=CartResponse)
def merge_cart(
    x_session_id: str = Header(...),
    user_id: str = Depends(lambda authorization=Header(None): get_identity(None, authorization)["user_id"]),
    db: Session = Depends(get_db),
):
    if not user_id:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Authorization is required"})
    return CartService(db).merge_guest_cart(user_id=user_id, session_id=x_session_id)
