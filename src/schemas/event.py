from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ProductEventRequest(BaseModel):
    idempotency_key: str
    event: str
    product_id: str
    sku_ids: List[str]
    reason: Optional[str] = None
    date: datetime
