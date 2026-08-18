from fastapi import APIRouter, HTTPException, Query

from src.schemas.catalog import CatalogProductCard
from src.services.similar_products_service import similar_products_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Similar Products"])


@router.get("/products/{product_id}/similar", response_model=list[CatalogProductCard])
def get_similar_products(product_id: str, limit: int = Query(8, ge=1, le=50)):
    try:
        result = similar_products_service.get_similar_products(product_id=product_id, limit=limit)
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Product not found"})
    return result
