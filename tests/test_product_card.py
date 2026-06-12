import pytest
from unittest.mock import patch


MOCK_B2B_PRODUCT = {
    "id": "product-1",
    "title": "iPhone 15 Pro Max",
    "description": "Флагманский смартфон Apple 2024 года",
    "slug": "iphone-15-pro-max",
    "status": "MODERATED",
    "deleted": False,
    "images": [
        {"url": "/s3/iphone15-front.jpg", "ordering": 0},
        {"url": "/s3/iphone15-back.jpg", "ordering": 1}
    ],
    "characteristics": [
        {"name": "Бренд", "value": "Apple"},
        {"name": "Страна-производитель", "value": "Китай"}
    ],
    "skus": [
        {
            "id": "sku-1",
            "name": "256GB Black",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 0,
            "image": "/s3/iphone15-black-256.jpg",
            "active_quantity": 10,
            "reserved_quantity": 2,
            "characteristics": [
                {"name": "Цвет", "value": "Чёрный"},
                {"name": "Объём памяти", "value": "256 ГБ"}
            ]
        },
        {
            "id": "sku-2",
            "name": "256GB White",
            "price": 12999000,
            "cost_price": 9500000,
            "discount": 500000,
            "image": "/s3/iphone15-white-256.jpg",
            "active_quantity": 3,
            "reserved_quantity": 0,
            "characteristics": [
                {"name": "Цвет", "value": "Белый"},
                {"name": "Объём памяти", "value": "256 ГБ"}
            ]
        }
    ]
}

MOCK_B2B_BLOCKED_PRODUCT = {
    "id": "product-blocked",
    "title": "Blocked Product",
    "description": "Blocked",
    "status": "BLOCKED",
    "deleted": False,
    "images": [],
    "characteristics": [],
    "skus": []
}

MOCK_B2B_DELETED_PRODUCT = {
    "id": "product-deleted",
    "title": "Deleted Product",
    "description": "Deleted",
    "status": "MODERATED",
    "deleted": True,
    "images": [],
    "characteristics": [],
    "skus": []
}


class TestProductCard:

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_product_card_returns_full_data_with_skus(self, mock_get_product, client):
        """Happy path: full product data with SKUs"""
        mock_get_product.return_value = MOCK_B2B_PRODUCT

        response = client.get("/api/v1/catalog/products/product-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "product-1"
        assert data["name"] == "iPhone 15 Pro Max"
        assert data["description"] == "Флагманский смартфон Apple 2024 года"
        assert len(data["images"]) == 2
        assert len(data["skus"]) == 2
        assert data["min_price"] == 12999000
        assert data["has_stock"] is True

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_cost_price_absent_in_response(self, mock_get_product, client):
        """cost_price and reserved_quantity must NOT be in response"""
        mock_get_product.return_value = MOCK_B2B_PRODUCT

        response = client.get("/api/v1/catalog/products/product-1")

        assert response.status_code == 200
        data = response.json()
        for sku in data["skus"]:
            assert "cost_price" not in sku
            assert "reserved_quantity" not in sku

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_blocked_product_returns_404(self, mock_get_product, client):
        """BLOCKED product → 404"""
        mock_get_product.return_value = MOCK_B2B_BLOCKED_PRODUCT

        response = client.get("/api/v1/catalog/products/product-blocked")

        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_deleted_product_returns_404(self, mock_get_product, client):
        """Deleted product → 404"""
        mock_get_product.return_value = MOCK_B2B_DELETED_PRODUCT

        response = client.get("/api/v1/catalog/products/product-deleted")

        assert response.status_code == 404

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_sku_without_stock_is_shown_as_unavailable(self, mock_get_product, client):
        """SKU with active_quantity=0 shown as unavailable"""
        product = MOCK_B2B_PRODUCT.copy()
        product["skus"] = [
            {
                "id": "sku-out",
                "name": "Out of Stock SKU",
                "price": 10000,
                "discount": 0,
                "image": None,
                "active_quantity": 0,
                "reserved_quantity": 0,
                "characteristics": []
            }
        ]
        mock_get_product.return_value = product

        response = client.get("/api/v1/catalog/products/product-1")

        assert response.status_code == 200
        data = response.json()
        assert data["skus"][0]["available_quantity"] == 0
        assert data["has_stock"] is False

    @patch('src.services.product_card_service.b2b_client.get_product_by_id')
    def test_discount_field_present(self, mock_get_product, client):
        """discount field is present in SKU"""
        mock_get_product.return_value = MOCK_B2B_PRODUCT

        response = client.get("/api/v1/catalog/products/product-1")

        assert response.status_code == 200
        data = response.json()
        assert data["skus"][1]["discount"] == 500000
