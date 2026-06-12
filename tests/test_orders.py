import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock
import httpx


MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15",
    "status": "MODERATED",
    "deleted": False,
    "images": [],
    "characteristics": [],
    "skus": [
        {
            "id": "sku-1",
            "name": "256GB Black",
            "price": 12999000,
            "active_quantity": 10,
            "image": "/s3/iphone.jpg",
            "characteristics": []
        }
    ]
}


class TestOrders:

    @patch('src.services.order_service.b2b_client.get_products')
    @patch('src.services.order_service.httpx.Client')
    def test_checkout_creates_paid_order_with_fixed_prices(self, MockClient, mock_get_products, client, valid_jwt):
        """Happy path: order created with fixed prices"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reserved": True, "items": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        MockClient.return_value = mock_client_instance

        response = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": str(uuid4()),
                "items": [{"sku_id": "sku-1", "quantity": 2}],
                "delivery_address": "г. Екатеринбург"
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PAID"
        assert data["total_amount"] == 12999000 * 2
        assert len(data["items"]) == 1
        assert data["items"][0]["unit_price"] == 12999000
        assert data["items"][0]["product_title"] == "iPhone 15"

    @patch('src.services.order_service.b2b_client.get_products')
    def test_partial_reserve_failure_returns_409(self, mock_get_products, client, valid_jwt):
        """Insufficient stock → 409"""
        product = MOCK_B2B_PRODUCT.copy()
        product["skus"] = [
            {
                "id": "sku-1",
                "name": "256GB Black",
                "price": 12999000,
                "active_quantity": 1,
                "image": "/s3/iphone.jpg",
                "characteristics": []
            }
        ]
        mock_get_products.return_value = {"items": [product], "total_count": 1}

        response = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": str(uuid4()),
                "items": [{"sku_id": "sku-1", "quantity": 5}]
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 409
        data = response.json()
        assert data["code"] == "RESERVE_FAILED"

    @patch('src.services.order_service.b2b_client.get_products')
    @patch('src.services.order_service.httpx.Client')
    def test_idempotency_returns_existing_order(self, MockClient, mock_get_products, client, valid_jwt):
        """Same idempotency_key → existing order"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"reserved": True, "items": []}
        mock_response.raise_for_status = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        MockClient.return_value = mock_client_instance

        idempotency_key = str(uuid4())

        response1 = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": idempotency_key,
                "items": [{"sku_id": "sku-1", "quantity": 1}]
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response1.status_code == 201

        response2 = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": idempotency_key,
                "items": [{"sku_id": "sku-1", "quantity": 1}]
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response2.status_code == 201
        assert response2.json()["id"] == response1.json()["id"]

    @patch('src.services.order_service.b2b_client.get_products')
    def test_b2b_unavailable_returns_503(self, mock_get_products, client, valid_jwt):
        """B2B unavailable → 503"""
        mock_get_products.side_effect = Exception("Connection refused")

        response = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": str(uuid4()),
                "items": [{"sku_id": "sku-1", "quantity": 1}]
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 503
        assert response.json()["code"] == "B2B_UNAVAILABLE"

    @patch('src.services.order_service.b2b_client.get_products')
    def test_empty_items_returns_400(self, mock_get_products, client, valid_jwt):
        """Empty items → 400"""
        response = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": str(uuid4()),
                "items": []
            },
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 400

    def test_unauthorized_returns_401(self, client):
        """No JWT → 401"""
        response = client.post(
            "/api/v1/orders",
            json={
                "idempotency_key": str(uuid4()),
                "items": [{"sku_id": "sku-1", "quantity": 1}]
            }
        )
        assert response.status_code == 401
