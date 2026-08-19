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

    def get_facets(self, category_id: str | None = None, attributes: dict | None = None) -> dict:
        """Build facets from the same attribute-rich public catalog response as the list."""
        b2b_data = b2b_client.get_products(
            limit=100,
            offset=0,
            category=category_id,
            filters=attributes,
        )
        counts: dict[str, dict[str, int]] = {}
        for item in b2b_data.get("items", []):
            characteristics = item.get("characteristics", []) or item.get("attributes", [])
            for characteristic in characteristics:
                name = characteristic.get("name") or characteristic.get("slug")
                value = characteristic.get("value")
                if not name or value is None:
                    continue
                value = str(value)
                values = counts.setdefault(str(name), {})
                values[value] = values.get(value, 0) + 1
        return {
            "category_id": category_id,
            "facets": [
                {
                    "name": name,
                    "values": [
                        {"value": value, "count": count}
                        for value, count in sorted(values.items(), key=lambda row: (-row[1], row[0]))
                    ],
                }
                for name, values in sorted(counts.items())
            ],
        }


catalog_service = CatalogService()
