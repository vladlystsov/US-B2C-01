import pytest
from uuid import uuid4
from datetime import date, timedelta
from src.models.collection import Collection, CollectionProduct


class TestCollections:

    def test_collections_list_returns_metadata_without_products(self, client, db_session):
        """Collections list returns metadata only, no products"""
        col = Collection(
            id=str(uuid4()),
            title="Хиты продаж",
            description="Лучшие товары",
            cover_image_url="/cdn/hits.jpg",
            target_url="/catalog?cat=hits",
            priority=10,
            is_active=True,
            start_date=date.today() - timedelta(days=1)
        )
        db_session.add(col)
        db_session.commit()

        response = client.get("/api/v1/main/collections")

        assert response.status_code == 200
        data = response.json()
        assert len(data["collections"]) == 1
        assert data["collections"][0]["title"] == "Хиты продаж"
        assert data["total_count"] == 1

    def test_collection_products_enriched_from_b2b(self, client, db_session):
        """Collection products enriched from B2B"""
        col = Collection(
            id=str(uuid4()),
            title="Test Collection",
            is_active=True,
            start_date=date.today() - timedelta(days=1)
        )
        db_session.add(col)
        db_session.commit()

        cp = CollectionProduct(
            collection_id=col.id,
            product_id="product-1",
            ordering=0
        )
        db_session.add(cp)
        db_session.commit()

        response = client.get(f"/api/v1/collections/{col.id}/products")

        assert response.status_code == 200
        data = response.json()
        assert data["collection_title"] == "Test Collection"

    def test_unknown_collection_returns_404(self, client, db_session):
        """Unknown collection → 404"""
        response = client.get(f"/api/v1/collections/{str(uuid4())}/products")

        assert response.status_code == 404

    def test_empty_collection_returns_empty_items(self, client, db_session):
        """Empty collection → items: []"""
        col = Collection(
            id=str(uuid4()),
            title="Empty Collection",
            is_active=True
        )
        db_session.add(col)
        db_session.commit()

        response = client.get(f"/api/v1/collections/{col.id}/products")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_products"] == 0

    def test_inactive_collections_excluded(self, client, db_session):
        """Inactive collections not shown"""
        db_session.query(CollectionProduct).delete()
        db_session.query(Collection).delete()
        db_session.commit()

        col = Collection(
            id=str(uuid4()),
            title="Inactive",
            is_active=False
        )
        db_session.add(col)
        db_session.commit()

        response = client.get("/api/v1/main/collections")

        assert response.status_code == 200
        assert len(response.json()["collections"]) == 0
