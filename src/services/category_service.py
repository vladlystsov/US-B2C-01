from src.services.b2b_client import b2b_client
import httpx


class CategoryService:
    def get_category_tree(self) -> dict:
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{b2b_client.base_url}/api/v1/categories/",
                    headers=b2b_client.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            return {"items": []}

    def get_category_detail(self, category_id: str, include_product_count: bool = False) -> dict | None:
        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{b2b_client.base_url}/api/v1/categories/{category_id}",
                    headers=b2b_client.headers,
                    timeout=10.0
                )
                response.raise_for_status()
                result = response.json()

                if include_product_count:
                    b2b_data = b2b_client.get_products(limit=100, offset=0, category=category_id)
                    result["product_count"] = len(b2b_data.get("items", []))

                return result
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception:
            return None

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

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{b2b_client.base_url}/api/v1/categories/{category_id}",
                    headers=b2b_client.headers,
                    timeout=10.0
                )
                if response.status_code == 404:
                    cat_name = "Unknown"
                else:
                    cat_data = response.json()
                    cat_name = cat_data.get("name", "Unknown")
        except Exception:
            cat_name = "Unknown"

        items = [
            {
                "id": category_id,
                "slug": None,
                "name": cat_name,
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
