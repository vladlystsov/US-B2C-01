from sqlalchemy.orm import Session
from src.models.banner import Banner, BannerEvent
from datetime import datetime
import uuid


class BannerService:
    def __init__(self, db: Session):
        self.db = db

    def get_active_banners(self) -> dict:
        now = datetime.utcnow()

        banners = self.db.query(Banner).filter(
            Banner.is_active == True
        ).all()

        active = []
        for banner in banners:
            if banner.start_at and banner.start_at > now:
                continue
            if banner.end_at and banner.end_at < now:
                continue

            active.append({
                "id": banner.id,
                "title": banner.title,
                "image_url": banner.image_url,
                "link": banner.link,
                "priority": banner.priority
            })

        active.sort(key=lambda x: x["priority"])

        return {"items": active, "total_count": len(active)}

    def track_event(self, banner_id: str, event: str, user_id: str = None) -> dict:
        banner = self.db.query(Banner).filter(Banner.id == banner_id).first()
        if not banner:
            return {"error": "BANNER_NOT_FOUND"}

        if event not in ["impression", "click"]:
            return {"error": "INVALID_EVENT"}

        banner_event = BannerEvent(
            id=str(uuid.uuid4()),
            banner_id=banner_id,
            user_id=user_id,
            event=event,
            timestamp=datetime.utcnow()
        )
        self.db.add(banner_event)
        self.db.commit()

        return {"status": "recorded"}
