from __future__ import annotations

from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_card


VALID_SORT_VALUES = ["price_asc", "price_desc", "popularity", "new"]


class CatalogService:
    def get_products(
        self,
        limit: int = 20,
        offset: int = 0,
        category_id: str | None = None,
        q: str | None = None,
        sort: str | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        seller_id: str | None = None,
        attributes: dict | None = None,
    ) -> dict:
        if sort and sort not in VALID_SORT_VALUES:
            raise ValueError(f"Invalid sort parameter. Allowed: {', '.join(VALID_SORT_VALUES)}")
        if q is not None:
            if len(q) < 3:
                raise ValueError("Search query must be at least 3 characters")
            if len(q) > 200:
                raise ValueError("Search query must be at most 200 characters")
        if price_min is not None and price_max is not None and price_min > price_max:
            raise ValueError("filter[price_min] must not exceed filter[price_max]")

        b2b_data = b2b_client.get_products(
            limit=limit,
            offset=offset,
            category=category_id,
            search=q,
            sort=sort,
            price_min=price_min,
            price_max=price_max,
            seller_id=seller_id,
            filters=attributes,
        )
        return {
            "items": [catalog_card(item) for item in b2b_data.get("items", [])],
            "total_count": b2b_data.get("total_count", 0),
            "limit": b2b_data.get("limit", limit),
            "offset": b2b_data.get("offset", offset),
        }

    def get_facets(self, category_id: str | None = None) -> dict:
        """Backward-compatible extension retained outside the published B2C surface."""
        b2b_data = b2b_client.get_products(limit=100, offset=0, category=category_id)
        brand_counts: dict[str, int] = {}
        for item in b2b_data.get("items", []):
            characteristics = item.get("characteristics", [])
            for char in characteristics if isinstance(characteristics, list) else []:
                if char.get("name") == "Бренд":
                    brand = char.get("value", "Unknown")
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1
        return {
            "category_id": category_id,
            "facets": ([{"name": "brand", "values": [{"value": key, "count": value} for key, value in sorted(brand_counts.items(), key=lambda row: -row[1])]}] if brand_counts else []),
        }


catalog_service = CatalogService()
