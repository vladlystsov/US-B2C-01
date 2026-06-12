from pydantic import BaseModel
from typing import List, Any


class FavoriteItem(BaseModel):
    product_id: str
    added_at: str


class FavoriteResponse(BaseModel):
    items: List[Any] = []
    total_count: int = 0
