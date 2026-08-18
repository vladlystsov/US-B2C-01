import httpx

from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_card


class SimilarProductsService:
    def get_similar_products(self, product_id: str, limit: int = 8) -> list[dict] | None:
        try:
            product = b2b_client.get_product_by_id(product_id)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        if not product:
            return None

        category_id = product.get("category_id") or product.get("category", {}).get("id")
        if not category_id:
            return []

        b2b_data = b2b_client.get_products(limit=min(limit, 8) + 1, offset=0, category=category_id)
        result = []
        for item in b2b_data.get("items", []):
            if str(item.get("id")) == str(product_id):
                continue
            result.append(catalog_card(item))
            if len(result) == min(limit, 8):
                break
        return result


similar_products_service = SimilarProductsService()
