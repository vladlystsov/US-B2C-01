from pydantic import BaseModel, Field
from typing import List, Optional, Any


class AddToCartRequest(BaseModel):
    sku_id: str
    quantity: int = Field(..., ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    id: str
    sku_id: str
    quantity: int
    product_id: Optional[str] = None
    title: Optional[str] = None
    image: Optional[str] = None
    price: Optional[int] = None
    available: bool = True
    unavailable_reason: Optional[str] = None


class CartSummary(BaseModel):
    total_amount: int = 0
    total_items: int = 0
    unavailable_count: int = 0
    checkout_ready: bool = True


class CartResponse(BaseModel):
    items: List[CartItemResponse] = []
    summary: CartSummary = CartSummary()
