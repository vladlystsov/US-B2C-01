from pydantic import BaseModel, Field
from typing import List, Optional, Any
from uuid import UUID


class ProductShortItem(BaseModel):
    id: str
    title: str
    image: Optional[str] = None
    price: int
    in_stock: bool = True
    is_in_cart: bool = False


class ProductShortListResponse(BaseModel):
    items: List[ProductShortItem] = []
    total_count: int = 0
    limit: int = 20
    offset: int = 0


class FacetValue(BaseModel):
    value: str
    count: int


class FacetItem(BaseModel):
    name: str
    values: List[FacetValue]


class FacetsResponse(BaseModel):
    category_id: Optional[str] = None
    facets: List[FacetItem] = []
