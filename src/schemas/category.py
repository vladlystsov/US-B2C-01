from pydantic import BaseModel
from typing import List, Optional, Any


class CategoryItem(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    children: List[Any] = []


class CategoryTreeResponse(BaseModel):
    items: List[CategoryItem] = []


class CategoryDetailResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    parent: Optional[dict] = None
    product_count: Optional[int] = None


class BreadcrumbItem(BaseModel):
    id: str
    slug: Optional[str] = None
    name: str
    url: str
    level: int
    is_current: bool


class BreadcrumbsResponse(BaseModel):
    data: List[BreadcrumbItem] = []
    meta: Optional[dict] = None
