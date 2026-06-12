from fastapi import APIRouter, HTTPException
from src.schemas.product_card import ProductPublicResponse
from src.services.product_card_service import product_card_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Product Card"])


@router.get("/products/{product_id}", response_model=ProductPublicResponse)
def get_product_card(product_id: str):
    result = product_card_service.get_product_card(product_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Product not found"}
        )

    return result
