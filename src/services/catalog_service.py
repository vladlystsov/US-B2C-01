from src.services.b2b_client import b2b_client


VALID_SORT_VALUES = ["rating", "popularity", "price_asc", "price_desc", "date_desc", "discount_desc"]


class CatalogService:
    def get_products(
        self,
        limit: int = 20,
        offset: int = 0,
        category_id: str = None,
        search: str = None,
        sort: str = None
    ) -> dict:
        if sort and sort not in VALID_SORT_VALUES:
            raise ValueError(f"Invalid sort parameter. Allowed: {', '.join(VALID_SORT_VALUES)}")

        b2b_data = b2b_client.get_products(
            limit=limit,
            offset=offset,
            category=category_id,
            search=search,
            sort=sort
        )

        items = []
        for item in b2b_data.get("items", []):
            skus = item.get("skus", [])
            min_price = min((s.get("price", 0) for s in skus if s.get("active_quantity", 0) > 0), default=0)
            in_stock = any(s.get("active_quantity", 0) > 0 for s in skus)
            image = None
            for s in skus:
                if s.get("image"):
                    image = s["image"]
                    break
            if not image and item.get("images"):
                image = item["images"][0].get("url") if isinstance(item["images"][0], dict) else item["images"][0]

            items.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "image": image,
                "price": min_price,
                "in_stock": in_stock,
                "is_in_cart": False
            })

        return {
            "items": items,
            "total_count": b2b_data.get("total_count", 0),
            "limit": limit,
            "offset": offset
        }

    def get_facets(self, category_id: str = None) -> dict:
        b2b_data = b2b_client.get_products(
            limit=100,
            offset=0,
            category=category_id
        )

        brand_counts = {}
        for item in b2b_data.get("items", []):
            for char in item.get("characteristics", []):
                if char.get("name") == "Бренд":
                    brand = char.get("value", "Unknown")
                    brand_counts[brand] = brand_counts.get(brand, 0) + 1

        facets = []
        if brand_counts:
            facets.append({
                "name": "brand",
                "values": [{"value": k, "count": v} for k, v in sorted(brand_counts.items(), key=lambda x: -x[1])]
            })

        return {
            "category_id": category_id,
            "facets": facets
        }


catalog_service = CatalogService()
