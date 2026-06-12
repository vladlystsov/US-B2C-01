from fastapi import APIRouter, Depends, HTTPException, Header
from src.schemas.banner import BannerListResponse, BannerEventRequest
from src.services.banner_service import BannerService
from src.database import get_db
from sqlalchemy.orm import Session
from typing import Optional


router = APIRouter(tags=["Banners"])


@router.get("/api/v1/home/banners", response_model=BannerListResponse)
def get_banners(db: Session = Depends(get_db)):
    service = BannerService(db)
    return service.get_active_banners()


@router.post("/api/v1/banner-events")
def track_banner_event(
    request: BannerEventRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None)
):
    user_id = None
    if authorization and authorization.startswith("Bearer "):
        from jose import jwt
        from src.config import settings
        token = authorization.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
        except Exception:
            pass

    service = BannerService(db)
    result = service.track_event(request.banner_id, request.event, user_id)

    if result.get("error") == "BANNER_NOT_FOUND":
        raise HTTPException(status_code=400, detail={"code": "BANNER_NOT_FOUND", "message": "Banner not found"})

    if result.get("error") == "INVALID_EVENT":
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": "Invalid event type"})

    return result
