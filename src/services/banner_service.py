import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.banner import Banner, BannerEvent


class BannerService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_banners(self) -> list[dict]:
        now = datetime.utcnow()
        banners = self.db.query(Banner).filter(Banner.is_active.is_(True)).all()
        active = []
        for banner in banners:
            if banner.start_at and banner.start_at > now:
                continue
            if banner.end_at and banner.end_at < now:
                continue
            active.append(
                {
                    "id": banner.id,
                    "title": banner.title,
                    "image_url": banner.image_url,
                    "link": banner.link,
                    "ordering": banner.priority,
                    "active_from": str(banner.start_at) if banner.start_at else None,
                    "active_to": str(banner.end_at) if banner.end_at else None,
                }
            )
        return sorted(active, key=lambda banner: banner["ordering"])

    def track_event(self, banner_id: str, event: str, user_id: str | None = None) -> dict:
        banner = self.db.query(Banner).filter(Banner.id == banner_id).first()
        if not banner:
            return {"error": "BANNER_NOT_FOUND"}
        if event not in ["impression", "click"]:
            return {"error": "INVALID_EVENT"}
        self.db.add(BannerEvent(id=str(uuid.uuid4()), banner_id=banner_id, user_id=user_id, event=event, timestamp=datetime.utcnow()))
        self.db.commit()
        return {"status": "recorded"}
