from typing import Optional

from pydantic import BaseModel, Field


class OrderItemSnapshot(BaseModel):
    sku_id: str
    quantity: int = Field(..., ge=1)
    unit_price: int = Field(..., ge=0)


class OrderCreateRequest(BaseModel):
    address_id: str
    payment_method_id: str
    comment: Optional[str] = Field(None, max_length=1000)
    items_snapshot: Optional[list[OrderItemSnapshot]] = None


class OrderItemResponse(BaseModel):
    sku_id: str
    product_id: str
    name: str
    sku_code: Optional[str] = None
    quantity: int
    unit_price: int
    line_total: int
    image_url: Optional[str] = None


class AddressResponse(BaseModel):
    id: str
    country: str
    city: str
    street: str
    building: str
    created_at: str
    region: Optional[str] = None
    apartment: Optional[str] = None
    postal_code: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_phone: Optional[str] = None
    is_default: bool = False
    comment: Optional[str] = None


class OrderStatusHistoryItem(BaseModel):
    status: str
    changed_at: str
    reason: Optional[str] = None


class OrderResponse(BaseModel):
    id: str
    buyer_id: str
    status: str
    items: list[OrderItemResponse] = Field(default_factory=list)
    subtotal: int
    delivery_cost: int = 0
    total: int
    address: AddressResponse
    payment_method: Optional[dict] = None
    comment: Optional[str] = None
    cancel_reason: Optional[str] = None
    status_history: list[OrderStatusHistoryItem] = Field(default_factory=list)
    created_at: str
    paid_at: Optional[str] = None
    delivered_at: Optional[str] = None
