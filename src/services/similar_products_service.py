import httpx

from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_card


class SimilarProductsService:
    def get_similar_products(self, product_id: str, limit: int = 10) -> list[dict] | None:
        try:
            items = b2b_client.get_similar_products(product_id, limit=limit)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise
        return [catalog_card(item) for item in items if str(item.get("id")) != str(product_id)][:limit]


similar_products_service = SimilarProductsService()
