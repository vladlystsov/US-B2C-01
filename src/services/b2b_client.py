from __future__ import annotations

import httpx

from src.config import settings


class B2BClient:
    def __init__(self):
        self.base_url = settings.B2B_SERVICE_URL
        self.headers = {"X-Service-Key": settings.B2B_SERVICE_KEY}

    def get_products(
        self,
        limit: int = 20,
        offset: int = 0,
        category: str | None = None,
        search: str | None = None,
        sort: str | None = None,
        ids: str | list[str] | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        seller_id: str | None = None,
        filters: dict | None = None,
    ) -> dict:
        """Load only B2B public-catalog data available to B2C."""
        if ids:
            product_ids = ids.split(",") if isinstance(ids, str) else ids
            return {
                "items": self.get_products_batch(product_ids),
                "total_count": len(product_ids),
                "limit": limit,
                "offset": offset,
            }

        sort_map = {"popularity": "popular", "new": "created_desc"}
        params: dict = {"limit": limit, "offset": offset}
        if category:
            params["category_id"] = category
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort_map.get(sort, sort)
        if price_min is not None:
            params["min_price"] = price_min
        if price_max is not None:
            params["max_price"] = price_max
        if seller_id:
            params["seller_id"] = seller_id
        if filters:
            for key, value in filters.items():
                params[f"filters[{key}]"] = value

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/public/products",
                params=params,
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    def get_products_batch(self, product_ids: list[str]) -> list[dict]:
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/api/v1/public/products/batch",
                json={"product_ids": product_ids},
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("items", [])

    def get_product_by_id(self, product_id: str) -> dict:
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/public/products/{product_id}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    def get_public_sku(self, sku_id: str) -> dict:
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/public/skus/{sku_id}",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            return response.json()

    def get_categories(self) -> list[dict]:
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/categories",
                headers=self.headers,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else data.get("items", [])


b2b_client = B2BClient()
