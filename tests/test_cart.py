import pytest
from uuid import uuid4
from unittest.mock import patch


MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15",
    "status": "MODERATED",
    "images": [{"url": "/s3/iphone15.jpg", "ordering": 0}],
    "characteristics": [],
    "skus": [
        {
            "id": "sku-1",
            "name": "256GB Black",
            "price": 12999000,
            "active_quantity": 10,
            "image": "/s3/iphone15-black.jpg",
            "characteristics": []
        }
    ]
}


class TestCart:

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_add_sku_increments_quantity_if_already_in_cart(self, mock_get_products, client, valid_jwt):
        """Repeat add of same SKU increments quantity"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        response1 = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 2},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response1.status_code == 201

        response2 = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 3},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert response2.status_code == 201
        assert response2.json()["quantity"] == 5

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_get_cart_enriched_with_b2b_data(self, mock_get_products, client, valid_jwt):
        """GET /cart returns enriched data from B2B"""
        mock_get_products.return_value = {"items": [MOCK_B2B_PRODUCT], "total_count": 1}

        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["title"] == "iPhone 15"
        assert data["items"][0]["price"] == 12999000

    @patch('src.services.cart_service.b2b_client.get_products')
    def test_unavailable_sku_shown_with_reason(self, mock_get_products, client, valid_jwt):
        """Unavailable SKU shown with unavailable_reason"""
        product = MOCK_B2B_PRODUCT.copy()
        product["skus"] = [
            {
                "id": "sku-1",
                "name": "256GB Black",
                "price": 12999000,
                "active_quantity": 0,
                "image": "/s3/iphone15-black.jpg",
                "characteristics": []
            }
        ]
        mock_get_products.return_value = {"items": [product], "total_count": 1}

        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["available"] is False
        assert data["items"][0]["unavailable_reason"] == "OUT_OF_STOCK"

    def test_guest_cart_works_with_session_id(self, client):
        """Guest cart works with X-Session-Id"""
        session_id = str(uuid4())

        response = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"X-Session-Id": session_id}
        )

        assert response.status_code == 201

    def test_missing_identity_returns_400(self, client):
        """No JWT and no session_id → 400"""
        response = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1}
        )

        assert response.status_code == 400

    def test_update_quantity(self, client, valid_jwt):
        """Update cart item quantity"""
        add_response = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        item_id = add_response.json()["item_id"]

        response = client.put(
            f"/api/v1/cart/items/{item_id}",
            json={"quantity": 5},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 200
        assert response.json()["quantity"] == 5

    def test_remove_item(self, client, valid_jwt):
        """Remove item from cart"""
        add_response = client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        item_id = add_response.json()["item_id"]

        response = client.delete(
            f"/api/v1/cart/items/{item_id}",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

    def test_clear_cart(self, client, valid_jwt):
        """Clear entire cart"""
        client.post(
            "/api/v1/cart/items",
            json={"sku_id": "sku-1", "quantity": 1},
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        response = client.delete(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )

        assert response.status_code == 204

        get_response = client.get(
            "/api/v1/cart",
            headers={"Authorization": f"Bearer {valid_jwt}"}
        )
        assert get_response.json()["items"] == []
