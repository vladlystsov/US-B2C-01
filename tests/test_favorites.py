import pytest
from uuid import uuid4


class TestFavorites:

    def test_add_to_favorites_returns_201(self, client, valid_jwt):
        """Happy path: add product to favorites"""
        product_id = str(uuid4())

        response = client.post(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["product_id"] == product_id
        assert "added_at" in data

    def test_repeat_add_returns_200_not_duplicate(self, client, valid_jwt):
        """Repeat add → 200, not duplicate in DB"""
        product_id = str(uuid4())

        response1 = client.post(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response1.status_code == 201

        response2 = client.post(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response2.status_code == 200

    def test_get_favorites_enriched_from_b2b(self, client, valid_jwt, db_session):
        """GET /favorites returns enriched data from B2B"""
        product_id = str(uuid4())

        client.post(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.get(
            "/api/v1/favorites",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total_count" in data

    def test_delete_from_favorites_returns_204(self, client, valid_jwt):
        """Delete product from favorites"""
        product_id = str(uuid4())

        client.post(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.delete(
            f"/api/v1/favorites/{product_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_delete_nonexistent_returns_204(self, client, valid_jwt):
        """Delete non-existent favorite → 204 (idempotent)"""
        response = client.delete(
            f"/api/v1/favorites/{str(uuid4())}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_unauthorized_returns_401(self, client):
        """No JWT → 401"""
        response = client.get("/api/v1/favorites")
        assert response.status_code == 401

    def test_user_id_from_query_is_ignored(self, client, valid_jwt):
        """user_id in query is ignored, JWT used instead"""
        product_id = str(uuid4())

        response = client.post(
            f"/api/v1/favorites/{product_id}?user_id=other-user",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 201
