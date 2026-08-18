from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.catalog import CatalogProductCard


class CollectionMetadata(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    products: list[CatalogProductCard] = Field(default_factory=list)


class CollectionProductsResponse(CollectionMetadata):
    unavailable_ids: list[str] = Field(default_factory=list)
