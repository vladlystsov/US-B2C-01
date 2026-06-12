from pydantic import BaseModel
from typing import List, Optional, Any


class CollectionMetadata(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    target_url: Optional[str] = None
    priority: int = 0


class CollectionsListResponse(BaseModel):
    collections: List[CollectionMetadata] = []
    total_count: int = 0


class CollectionProductsResponse(BaseModel):
    collection_title: str
    items: List[Any] = []
    unavailable_ids: List[str] = []
    total_products: int = 0
