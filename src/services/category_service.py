from src.services.b2b_client import b2b_client
import httpx


class CategoryService:
    def get_category_tree(self) -> dict:
        b2b_data = b2b_client.get_products(limit=100, offset=0)

        categories = {}
        for item in b2b_data.get("items", []):
            cat = item.get("category", {})
            if cat and cat.get("id"):
                cat_id = cat["id"]
                if cat_id not in categories:
                    categories[cat_id] = {
                        "id": cat_id,
                        "name": cat.get("name", "Unknown"),
                        "parent_id": None,
                        "children": []
                    }

        return {"items": list(categories.values())}

    def get_category_detail(self, category_id: str, include_product_count: bool = False) -> dict | None:
        try:
            b2b_data = b2b_client.get_products(limit=100, offset=0, category=category_id)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

        if not b2b_data.get("items"):
            return None

        product_count = len(b2b_data.get("items", [])) if include_product_count else None

        return {
            "id": category_id,
            "name": "Category",
            "slug": None,
            "description": None,
            "parent": None,
            "product_count": product_count
        }

    def get_breadcrumbs(self, category_id: str = None, product_id: str = None) -> dict | None:
        if category_id and product_id:
            return {"error": "ambiguous_param"}

        if not category_id and not product_id:
            return {"error": "missing_param"}

        resolved_via = "category_id"

        if product_id:
            resolved_via = "product_id"
            try:
                product = b2b_client.get_product_by_id(product_id)
            except httpx.HTTPStatusError:
                return None
            if not product:
                return None
            category_id = product.get("category", {}).get("id")
            if not category_id:
                return {"data": [], "meta": {"resolved_via": "product_id", "product_id": product_id}}

        items = [
            {
                "id": category_id,
                "slug": None,
                "name": "Category",
                "url": f"/catalog/{category_id}",
                "level": 0,
                "is_current": True
            }
        ]

        return {
            "data": items,
            "meta": {"resolved_via": resolved_via, "category_id": category_id}
        }


category_service = CategoryService()
