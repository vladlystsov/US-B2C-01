from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.catalog import ImageRef


class AddToCartRequest(BaseModel):
    sku_id: str
    quantity: int = Field(..., ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(..., ge=1)


class CartItemResponse(BaseModel):
    sku_id: str
    product_id: str
    name: str
    sku_code: Optional[str] = None
    quantity: int
    unit_price: int
    unit_price_at_add: Optional[int] = None
    line_total: int
    available_quantity: int
    is_available: bool
    unavailable_reason: Optional[str] = None
    image: Optional[ImageRef] = None


class CartResponse(BaseModel):
    id: Optional[str] = None
    items: list[CartItemResponse] = Field(default_factory=list)
    items_count: int = 0
    subtotal: int = 0
    is_valid: bool = True
