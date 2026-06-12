import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from src.models.banner import Banner, BannerEvent
from src.database import Base


class TestBanners:

    def test_active_banners_returned_sorted_by_priority(self, client, db_session):
        """Only active banners within schedule, sorted by priority"""
        now = datetime.utcnow()

        banner1 = Banner(
            id=str(uuid4()),
            title="Sale 30%",
            image_url="/cdn/sale.jpg",
            link="/catalog?cat=1",
            priority=20,
            is_active=True,
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=1)
        )
        banner2 = Banner(
            id=str(uuid4()),
            title="New Collection",
            image_url="/cdn/new.jpg",
            link="/catalog?cat=2",
            priority=5,
            is_active=True,
            start_at=now - timedelta(days=1),
            end_at=now + timedelta(days=1)
        )
        db_session.add_all([banner1, banner2])
        db_session.commit()

        response = client.get("/api/v1/home/banners")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["priority"] == 5
        assert data["items"][1]["priority"] == 20

    def test_no_active_banners_returns_200_empty(self, client, db_session):
        """No active banners → 200 with empty list"""
        db_session.query(Banner).delete()
        db_session.commit()

        response = client.get("/api/v1/home/banners")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    def test_inactive_banners_excluded(self, client, db_session):
        """Inactive banners not shown"""
        db_session.query(Banner).delete()
        db_session.commit()

        banner = Banner(
            id=str(uuid4()),
            title="Inactive",
            image_url="/cdn/inactive.jpg",
            link="/catalog",
            priority=10,
            is_active=False
        )
        db_session.add(banner)
        db_session.commit()

        response = client.get("/api/v1/home/banners")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

    def test_expired_banners_excluded(self, client, db_session):
        """Expired banners not shown"""
        db_session.query(Banner).delete()
        db_session.commit()

        banner = Banner(
            id=str(uuid4()),
            title="Expired",
            image_url="/cdn/expired.jpg",
            link="/catalog",
            priority=10,
            is_active=True,
            start_at=datetime.utcnow() - timedelta(days=10),
            end_at=datetime.utcnow() - timedelta(days=1)
        )
        db_session.add(banner)
        db_session.commit()

        response = client.get("/api/v1/home/banners")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

    def test_click_on_unknown_banner_returns_400(self, client, db_session):
        """Click on unknown banner → 400"""
        response = client.post(
            "/api/v1/banner-events",
            json={"banner_id": str(uuid4()), "event": "click"}
        )

        assert response.status_code == 400
        assert response.json()["code"] == "BANNER_NOT_FOUND"

    def test_banner_event_recorded(self, client, db_session):
        """Banner event is recorded"""
        banner = Banner(
            id=str(uuid4()),
            title="Test Banner",
            image_url="/cdn/test.jpg",
            link="/catalog",
            priority=10,
            is_active=True
        )
        db_session.add(banner)
        db_session.commit()

        response = client.post(
            "/api/v1/banner-events",
            json={"banner_id": banner.id, "event": "click"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "recorded"
