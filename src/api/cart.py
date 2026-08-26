from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.schemas.cart import AddToCartRequest, CartResponse, CartValidationResponse, UpdateCartItemRequest
from src.services.cart_service import CartService

router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])


def get_identity(x_session_id: Optional[str] = Header(None), authorization: Optional[str] = Header(None)):
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid authorization scheme"})
        try:
            user_id = jwt.decode(
                authorization.split(" ", 1)[1], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            ).get("sub")
        except (JWTError, IndexError):
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"})
        if not user_id:
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Invalid token subject"})
        return {"user_id": user_id, "session_id": None}
    if x_session_id:
        return {"user_id": None, "session_id": x_session_id}
    raise HTTPException(status_code=400, detail={"code": "MISSING_CART_IDENTITY", "message": "Provide Authorization header or X-Session-Id"})


@router.get("", response_model=CartResponse)
def get_cart(identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    return CartService(db).get_cart(**identity)


def _raise_cart_error(result: dict) -> None:
    code = result.get("error")
    if not code:
        return
    status_code = {
        "B2B_UNAVAILABLE": 502,
        "NOT_FOUND": 404,
        "SKU_NOT_FOUND": 404,
        "SKU_UNAVAILABLE": 404,
        "INSUFFICIENT_STOCK": 409,
    }.get(code, 409)
    if code == "MISSING_IDENTITY":
        status_code = 400
    raise HTTPException(status_code=status_code, detail={"code": result["code"], "message": result["message"]})


@router.post("/validate", response_model=CartValidationResponse)
def validate_cart(identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    return CartService(db).validate_cart(**identity)


@router.post("/items", response_model=CartResponse)
def add_to_cart(request: AddToCartRequest, identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    result = CartService(db).add_item(str(request.sku_id), request.quantity, **identity)
    _raise_cart_error(result)
    return result


@router.patch("/items/{sku_id}", response_model=CartResponse)
def update_cart_item(
    sku_id: UUID,
    request: UpdateCartItemRequest,
    identity: dict = Depends(get_identity),
    db: Session = Depends(get_db),
):
    result = CartService(db).update_item(str(sku_id), request.quantity, **identity)
    _raise_cart_error(result)
    return result


@router.delete("/items/{sku_id}", response_model=CartResponse)
def remove_from_cart(sku_id: UUID, identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    result = CartService(db).remove_item(str(sku_id), **identity)
    _raise_cart_error(result)
    return result


@router.delete("", status_code=204)
def clear_cart(identity: dict = Depends(get_identity), db: Session = Depends(get_db)):
    CartService(db).clear_cart(**identity)
    return Response(status_code=204)


def require_authenticated_user_id(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Authorization is required"})
    return get_identity(authorization=authorization)["user_id"]


@router.post("/merge", response_model=CartResponse)
def merge_cart(
    x_session_id: str = Header(...),
    user_id: str = Depends(require_authenticated_user_id),
    db: Session = Depends(get_db),
):
    return CartService(db).merge_guest_cart(user_id=user_id, session_id=x_session_id)
