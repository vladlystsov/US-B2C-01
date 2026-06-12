from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class BannerItem(BaseModel):
    id: str
    title: str
    image_url: str
    link: str
    priority: int


class BannerListResponse(BaseModel):
    items: List[BannerItem] = []
    total_count: int = 0


class BannerEventRequest(BaseModel):
    banner_id: str
    event: str
