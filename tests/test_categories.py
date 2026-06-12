import pytest
from unittest.mock import patch


MOCK_B2B_PRODUCTS_FOR_TREE = {
    "items": [
        {
            "id": "product-1",
            "title": "iPhone",
            "category": {"id": "cat-electronics", "name": "Электроника"},
            "status": "MODERATED",
            "images": [],
            "characteristics": [],
            "skus": []
        },
        {
            "id": "product-2",
            "title": "Samsung",
            "category": {"id": "cat-electronics", "name": "Электроника"},
            "status": "MODERATED",
            "images": [],
            "characteristics": [],
            "skus": []
        },
        {
            "id": "product-3",
            "title": "T-Shirt",
            "category": {"id": "cat-clothes", "name": "Одежда"},
            "status": "MODERATED",
            "images": [],
            "characteristics": [],
            "skus": []
        }
    ],
    "total_count": 3,
    "limit": 100,
    "offset": 0
}


class TestCategories:

    @patch('src.services.category_service.b2b_client.get_products')
    def test_category_tree_returns_nested_structure(self, mock_get_products, client):
        """Category tree builds nested structure from flat list"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_FOR_TREE

        response = client.get("/api/v1/categories")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2
        names = [item["name"] for item in data["items"]]
        assert "Электроника" in names
        assert "Одежда" in names

    @patch('src.services.category_service.b2b_client.get_products')
    def test_category_detail_returns_category(self, mock_get_products, client):
        """Category detail returns category info"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_FOR_TREE

        response = client.get("/api/v1/categories/cat-electronics?include_product_count=true")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "cat-electronics"
        assert data["product_count"] is not None

    @patch('src.services.category_service.b2b_client.get_products')
    def test_unknown_category_returns_404(self, mock_get_products, client):
        """Unknown category → 404"""
        mock_get_products.return_value = {
            "items": [],
            "total_count": 0,
            "limit": 100,
            "offset": 0
        }

        response = client.get("/api/v1/categories/unknown-cat")

        assert response.status_code == 404

    def test_ambiguous_params_returns_400(self, client):
        """Both category_id and product_id → 400"""
        response = client.get("/api/v1/breadcrumbs?category_id=cat-1&product_id=prod-1")

        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "INVALID_REQUEST"

    def test_missing_params_returns_400(self, client):
        """Neither category_id nor product_id → 400"""
        response = client.get("/api/v1/breadcrumbs")

        assert response.status_code == 400

    @patch('src.services.category_service.b2b_client.get_products')
    def test_breadcrumbs_return_path_from_root(self, mock_get_products, client):
        """Breadcrumbs return path from root"""
        mock_get_products.return_value = MOCK_B2B_PRODUCTS_FOR_TREE

        response = client.get("/api/v1/breadcrumbs?category_id=cat-electronics")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["id"] == "cat-electronics"
        assert data["data"][0]["is_current"] is True

    @patch('src.services.category_service.b2b_client.get_product_by_id')
    def test_breadcrumbs_with_product_id(self, mock_get_product, client):
        """Breadcrumbs with product_id resolves category"""
        mock_get_product.return_value = {
            "id": "prod-1",
            "category": {"id": "cat-electronics", "name": "Электроника"}
        }

        response = client.get("/api/v1/breadcrumbs?product_id=prod-1")

        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["resolved_via"] == "product_id"
