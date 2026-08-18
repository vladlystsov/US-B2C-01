from src.services.b2b_client import b2b_client
from src.services.catalog_mapper import catalog_detail


class ProductCardService:
    def get_product_card(self, product_id: str) -> dict | None:
        b2b_data = b2b_client.get_product_by_id(product_id)
        if not b2b_data:
            return None
        if b2b_data.get("status") != "MODERATED" or b2b_data.get("deleted"):
            return None
        return catalog_detail(b2b_data)


product_card_service = ProductCardService()
