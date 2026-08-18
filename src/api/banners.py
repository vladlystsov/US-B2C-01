from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from jose import jwt
from sqlalchemy.orm import Session

from src.config import settings
from src.database import get_db
from src.schemas.banner import BannerEventRequest, BannerItem
from src.services.banner_service import BannerService

router = APIRouter(tags=["Banners"])


@router.get("/api/v1/catalog/banners", response_model=list[BannerItem])
def get_banners(db: Session = Depends(get_db)):
    return BannerService(db).get_active_banners()


@router.post("/api/v1/banner-events", include_in_schema=False)
def track_banner_event(
    request: BannerEventRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        try:
            user_id = jwt.decode(
                authorization.split(" ", 1)[1], settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            ).get("sub")
        except Exception:
            pass
    result = BannerService(db).track_event(request.banner_id, request.event, user_id)
    if result.get("error") == "BANNER_NOT_FOUND":
        raise HTTPException(status_code=400, detail={"code": "BANNER_NOT_FOUND", "message": "Banner not found"})
    if result.get("error") == "INVALID_EVENT":
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": "Invalid event type"})
    return result
