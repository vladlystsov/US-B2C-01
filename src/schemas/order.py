from pydantic import BaseModel, Field
from typing import List, Optional


class OrderItemRequest(BaseModel):
    sku_id: str
    quantity: int = Field(..., ge=1)


class OrderCreateRequest(BaseModel):
    idempotency_key: str
    items: List[OrderItemRequest]
    delivery_address: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: str
    sku_id: str
    product_id: str
    product_title: str
    sku_name: str
    quantity: int
    unit_price: int
    line_total: int


class OrderResponse(BaseModel):
    id: str
    status: str
    items: List[OrderItemResponse] = []
    total_amount: int = 0
    delivery_address: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
