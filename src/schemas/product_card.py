from pydantic import BaseModel
from typing import List, Optional, Any
from uuid import UUID


class SKUPublicResponse(BaseModel):
    id: str
    name: str
    price: int
    discount: int = 0
    image: Optional[str] = None
    available_quantity: int = 0
    characteristics: List[Any] = []


class ProductPublicResponse(BaseModel):
    id: str
    name: str
    description: str
    slug: Optional[str] = None
    images: List[Any] = []
    characteristics: List[Any] = []
    skus: List[SKUPublicResponse] = []
    min_price: int = 0
    has_stock: bool = False
