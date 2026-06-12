from src.services.b2b_client import b2b_client
import httpx


class SimilarProductsService:
    def get_similar_products(
        self,
        product_id: str,
        category_id: str = None,
        limit: int = 8,
        offset: int = 0
    ) -> dict:
        if not category_id:
            try:
                product = b2b_client.get_product_by_id(product_id)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise
            if not product:
                return None
            category_id = product.get("category", {}).get("id")
            if not category_id:
                return {"items": [], "total_count": 0, "limit": limit, "offset": offset}

        b2b_data = b2b_client.get_products(
            limit=limit + 1,
            offset=0,
            category=category_id
        )

        items = []
        for item in b2b_data.get("items", []):
            if str(item.get("id")) == str(product_id):
                continue

            skus = item.get("skus", [])
            min_price = min((s.get("price", 0) for s in skus if s.get("active_quantity", 0) > 0), default=0)
            in_stock = any(s.get("active_quantity", 0) > 0 for s in skus)
            image = None
            for s in skus:
                if s.get("image"):
                    image = s["image"]
                    break
            if not image and item.get("images"):
                image = item["images"][0].get("url") if isinstance(item["images"][0], dict) else item["images"]

            items.append({
                "id": item.get("id"),
                "title": item.get("title"),
                "image": image,
                "price": min_price,
                "in_stock": in_stock,
                "is_in_cart": False
            })

            if len(items) >= limit:
                break

        return {
            "items": items,
            "total_count": len(items),
            "limit": limit,
            "offset": offset
        }


similar_products_service = SimilarProductsService()
