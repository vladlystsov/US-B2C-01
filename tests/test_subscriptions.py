import pytest
from uuid import uuid4


class TestSubscriptions:

    def test_subscribe_returns_201_with_notify_on(self, client, valid_jwt):
        """Happy path: create subscription"""
        product_id = str(uuid4())

        response = client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": ["IN_STOCK", "PRICE_DOWN"]},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert "created_at" in data

    def test_duplicate_subscription_returns_409(self, client, valid_jwt):
        """Duplicate subscription → 409"""
        product_id = str(uuid4())

        client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": ["IN_STOCK"]},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": ["IN_STOCK"]},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 409
        assert response.json()["code"] == "SUBSCRIPTION_ALREADY_EXISTS"

    def test_invalid_notify_on_returns_400(self, client, valid_jwt):
        """Invalid notify_on → 400"""
        product_id = str(uuid4())

        response = client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": ["INVALID_VALUE"]},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_REQUEST"

    def test_empty_notify_on_returns_400(self, client, valid_jwt):
        """Empty notify_on → 400"""
        product_id = str(uuid4())

        response = client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": []},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 400

    def test_unsubscribe_returns_204(self, client, valid_jwt):
        """Unsubscribe from product"""
        product_id = str(uuid4())

        client.post(
            f"/api/v1/favorites/{product_id}/subscribe",
            json={"notify_on": ["IN_STOCK"]},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.delete(
            f"/api/v1/favorites/{product_id}/subscribe",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_unsubscribe_nonexistent_returns_204(self, client, valid_jwt):
        """Unsubscribe non-existent → 204 (idempotent)"""
        response = client.delete(
            f"/api/v1/favorites/{str(uuid4())}/subscribe",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_unauthorized_returns_401(self, client):
        """No JWT → 401"""
        response = client.post(
            f"/api/v1/favorites/{str(uuid4())}/subscribe",
            json={"notify_on": ["IN_STOCK"]}
        )
        assert response.status_code == 401
