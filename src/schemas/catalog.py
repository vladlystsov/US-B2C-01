from typing import Any, Optional

from pydantic import BaseModel, Field


class ImageRef(BaseModel):
    id: str
    url: str
    alt: Optional[str] = None
    ordering: int = 0
    is_main: Optional[bool] = None


class CatalogProductCard(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    min_price: int
    old_price: Optional[int] = None
    has_stock: bool
    rating: Optional[float] = None
    reviews_count: int = 0
    images: list[ImageRef] = Field(default_factory=list)


class ProductShortListResponse(BaseModel):
    items: list[CatalogProductCard] = Field(default_factory=list)
    total_count: int = 0
    limit: int = 20
    offset: int = 0


class FacetValue(BaseModel):
    value: str
    count: int


class FacetItem(BaseModel):
    name: str
    values: list[FacetValue]


class FacetsResponse(BaseModel):
    category_id: Optional[str] = None
    facets: list[FacetItem] = Field(default_factory=list)
