from typing import Optional

from pydantic import BaseModel


class BannerItem(BaseModel):
    id: str
    image_url: str
    link: str
    title: Optional[str] = None
    ordering: Optional[int] = None
    active_from: Optional[str] = None
    active_to: Optional[str] = None


class BannerEventRequest(BaseModel):
    banner_id: str
    event: str
