from typing import Any, Optional

from pydantic import BaseModel, Field

from src.schemas.catalog import CatalogProductCard, ImageRef


class SKUPublicResponse(BaseModel):
    id: str
    name: Optional[str] = None
    sku_code: Optional[str] = None
    price: int
    old_price: Optional[int] = None
    available_quantity: int = 0
    attributes: Any = Field(default_factory=dict)
    images: list[ImageRef] = Field(default_factory=list)


class ProductPublicResponse(CatalogProductCard):
    description: str
    attributes: Any = Field(default_factory=dict)
    skus: list[SKUPublicResponse] = Field(default_factory=list)
