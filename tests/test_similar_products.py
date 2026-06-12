import pytest
from unittest.mock import patch


MOCK_B2B_SIMILAR_PRODUCTS = {
    "items": [
        {
            "id": "product-2",
            "title": "Samsung Galaxy S24",
            "description": "Smartphone",
            "status": "MODERATED",
            "category": {"id": "cat-1", "name": "Electronics"},
            "images": [{"url": "/s3/s24.jpg", "ordering": 0}],
            "characteristics": [{"name": "Бренд", "value": "Samsung"}],
            "skus": [
                {
                    "id": "sku-2",
                    "name": "128GB White",
                    "price": 8999000,
                    "discount": 0,
                    "image": "/s3/s24-white.jpg",
                    "active_quantity": 5,
                    "characteristics": []
                }
            ]
        },
        {
            "id": "product-3",
            "title": "Xiaomi 14",
            "description": "Smartphone",
            "status": "MODERATED",
            "category": {"id": "cat-1", "name": "Electronics"},
            "images": [{"url": "/s3/xiaomi14.jpg", "ordering": 0}],
            "characteristics": [{"name": "Бренд", "value": "Xiaomi"}],
            "skus": [
                {
                    "id": "sku-3",
                    "name": "256GB Black",
                    "price": 6999000,
                    "discount": 300000,
                    "image": "/s3/xiaomi14-black.jpg",
                    "active_quantity": 8,
                    "characteristics": []
                }
            ]
        }
    ],
    "total_count": 2,
    "limit": 9,
    "offset": 0
}

MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15",
    "category": {"id": "cat-1", "name": "Electronics"},
    "status": "MODERATED",
    "images": [],
    "characteristics": [],
    "skus": []
}


class TestSimilarProducts:

    @patch('src.services.similar_products_service.b2b_client.get_products')
    def test_similar_returns_up_to_8_from_same_category(self, mock_get_products, client):
        """Happy path: up to 8 similar products, current excluded"""
        mock_get_products.return_value = MOCK_B2B_SIMILAR_PRODUCTS

        response = client.get(
            "/api/v1/catalog/products/product-1/similar?category=cat-1&limit=8"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 8
        ids = [item["id"] for item in data["items"]]
        assert "product-1" not in ids

    @patch('src.services.similar_products_service.b2b_client.get_products')
    def test_empty_category_returns_200_empty_list(self, mock_get_products, client):
        """No similar products → 200 with empty list"""
        mock_get_products.return_value = {
            "items": [],
            "total_count": 0,
            "limit": 9,
            "offset": 0
        }

        response = client.get(
            "/api/v1/catalog/products/product-1/similar?category=empty-cat"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    @patch('src.services.similar_products_service.b2b_client.get_products')
    @patch('src.services.similar_products_service.b2b_client.get_product_by_id')
    def test_unknown_product_returns_404(self, mock_get_product, mock_get_products, client):
        """Unknown product → 404"""
        import httpx
        mock_response = httpx.Response(status_code=404)
        mock_get_product.side_effect = httpx.HTTPStatusError(
            message="Not found",
            request=httpx.Request("GET", "http://test"),
            response=mock_response
        )

        response = client.get(
            "/api/v1/catalog/products/unknown-id/similar"
        )

        assert response.status_code == 404

    @patch('src.services.similar_products_service.b2b_client.get_products')
    def test_limit_parameter_works(self, mock_get_products, client):
        """Limit parameter controls result count"""
        mock_get_products.return_value = MOCK_B2B_SIMILAR_PRODUCTS

        response = client.get(
            "/api/v1/catalog/products/product-1/similar?category=cat-1&limit=1"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1
