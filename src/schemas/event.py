from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class B2BEventRequest(BaseModel):
    event_type: Literal[
        "PRODUCT_BLOCKED",
        "PRODUCT_HARD_BLOCKED",
        "PRODUCT_DELETED",
        "SKU_OUT_OF_STOCK",
        "SKU_BACK_IN_STOCK",
        "PRICE_CHANGED",
    ]
    idempotency_key: str
    occurred_at: datetime
    payload: dict[str, Any]
