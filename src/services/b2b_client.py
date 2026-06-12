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
        category: str = None,
        search: str = None,
        sort: str = None,
        ids: str = None
    ) -> dict:
        params = {"limit": limit, "offset": offset}
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        if sort:
            params["sort"] = sort
        if ids:
            params["ids"] = ids

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/products",
                params=params,
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    def get_product_by_id(self, product_id: str) -> dict:
        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/api/v1/products/{product_id}",
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()


b2b_client = B2BClient()
