import pytest
from unittest.mock import patch, MagicMock
import httpx


class TestCategories:

    @patch('src.services.category_service.httpx.Client')
    def test_category_tree_returns_nested_structure(self, MockClient, client):
        """Category tree returns categories from B2B"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"id": "cat-electronics", "name": "Электроника", "parent_id": None, "children": []},
                {"id": "cat-clothes", "name": "Одежда", "parent_id": None, "children": []}
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        MockClient.return_value = mock_client_instance

        response = client.get("/api/v1/categories/")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) >= 2

    @patch('src.services.category_service.httpx.Client')
    def test_category_detail_returns_category(self, MockClient, client):
        """Category detail returns category info"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cat-electronics",
            "name": "Электроника",
            "slug": "electronics",
            "parent_id": None,
            "description": None,
            "is_active": True
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        MockClient.return_value = mock_client_instance

        with patch('src.services.category_service.b2b_client.get_products') as mock_get_products:
            mock_get_products.return_value = {
                "items": [{"id": "p1"}],
                "total_count": 1,
                "limit": 100,
                "offset": 0
            }

            response = client.get("/api/v1/categories/cat-electronics?include_product_count=true")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "cat-electronics"

    def test_unknown_category_returns_404(self, client):
        """Unknown category → 404"""
        response = client.get("/api/v1/categories/unknown-cat")
        assert response.status_code == 404

    def test_ambiguous_params_returns_400(self, client):
        """Both category_id and product_id → 400"""
        response = client.get("/api/v1/breadcrumbs?category_id=cat-1&product_id=prod-1")
        assert response.status_code == 400

    def test_missing_params_returns_400(self, client):
        """Neither category_id nor product_id → 400"""
        response = client.get("/api/v1/breadcrumbs")
        assert response.status_code == 400

    @patch('src.services.category_service.httpx.Client')
    def test_breadcrumbs_return_path_from_root(self, MockClient, client):
        """Breadcrumbs return path from root"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cat-electronics",
            "name": "Электроника"
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        MockClient.return_value = mock_client_instance

        response = client.get("/api/v1/breadcrumbs?category_id=cat-electronics")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert data["data"][0]["id"] == "cat-electronics"

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
