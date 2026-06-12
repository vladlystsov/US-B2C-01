import pytest
from unittest.mock import patch, MagicMock


MOCK_B2B_PRODUCTS_RESPONSE = {
    "items": [
        {
            "id": "product-1",
            "title": "iPhone 15 Pro Max",
            "description": "Smartphone",
            "status": "MODERATED",
            "category": {"id": "cat-1", "name": "Electronics"},
            "images": [{"url": "/s3/iphone15.jpg", "ordering": 0}],
            "characteristics": [
                {"name": "Бренд", "value": "Apple"},
                {"name": "Цвет", "value": "Чёрный"}
            ],
            "skus": [
                {
                    "id": "sku-1",
                    "name": "256GB Black",
                    "price": 12999000,
                    "discount": 0,
                    "image": "/s3/iphone15-black.jpg",
                    "active_quantity": 10,
                    "characteristics": []
                }
            ]
        },
        {
            "id": "product-2",
            "title": "Samsung Galaxy S24",
            "description": "Smartphone",
            "status": "MODERATED",
            "category": {"id": "cat-1", "name": "Electronics"},
            "images": [{"url": "/s3/s24.jpg", "ordering": 0}],
            "characteristics": [
                {"name": "Бренд", "value": "Samsung"},
                {"name": "Цвет", "value": "Белый"}
            ],
            "skus": [
                {
                    "id": "sku-2",
                    "name": "128GB White",
                    "price": 8999000,
                    "discount": 500000,
                    "image": "/s3/s24-white.jpg",
                    "active_quantity": 5,
                    "characteristics": []
                }
            ]
        }
    ],
    "total_count": 2,
    "limit": 20,
    "offset": 0
}


class TestCatalog:

    @patch('src.services.catalog_service.b2b_client.get_products')
    def test_catalog_returns_filtered_sorted_products(self, mock_get_products, client):
        """Happy path: filters, sorting, pagination work"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_RESPONSE

        response = client.get(
            "/api/v1/products?category_id=cat-1&sort=price_asc&limit=10&offset=0"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total_count"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert data["items"][0]["title"] == "iPhone 15 Pro Max"
        assert data["items"][0]["price"] == 12999000
        assert data["items"][0]["in_stock"] is True

    @patch('src.services.catalog_service.b2b_client.get_products')
    def test_facets_return_counts_per_filter_value(self, mock_get_products, client):
        """Facets return correct counts"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_RESPONSE

        response = client.get("/api/v1/catalog/facets?category_id=cat-1")

        assert response.status_code == 200
        data = response.json()
        assert data["category_id"] == "cat-1"
        assert len(data["facets"]) >= 1

        brand_facet = next((f for f in data["facets"] if f["name"] == "brand"), None)
        assert brand_facet is not None
        brand_values = {v["value"]: v["count"] for v in brand_facet["values"]}
        assert brand_values["Apple"] == 1
        assert brand_values["Samsung"] == 1

    def test_invalid_sort_returns_400(self, client):
        """Invalid sort returns 400 with allowed values"""
        response = client.get("/api/v1/products?sort=invalid_sort")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_REQUEST"
        assert "rating" in data["message"]
        assert "price_asc" in data["message"]

    @patch('src.services.catalog_service.b2b_client.get_products')
    def test_b2b_unavailable_returns_502(self, mock_get_products, client):
        """B2B unavailable returns 502"""
        mock_get_products.side_effect = Exception("Connection refused")

        response = client.get("/api/v1/products")

        assert response.status_code == 502
        data = response.json()
        assert data["code"] == "BAD_GATEWAY"

    @patch('src.services.catalog_service.b2b_client.get_products')
    def test_empty_catalog_returns_200(self, mock_get_products, client):
        """Empty catalog returns 200 with empty items"""
        mock_get_products.return_value = {
            "items": [],
            "total_count": 0,
            "limit": 20,
            "offset": 0
        }

        response = client.get("/api/v1/products?category_id=empty-cat")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_count"] == 0

    @patch('src.services.catalog_service.b2b_client.get_products')
    def test_search_parameter_passed_to_b2b(self, mock_get_products, client):
        """Search parameter is passed to B2B"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_RESPONSE

        response = client.get("/api/v1/products?search=iPhone")

        assert response.status_code == 200
        mock_get_products.assert_called_once_with(
            limit=20,
            offset=0,
            category=None,
            search="iPhone",
            sort=None
        )
