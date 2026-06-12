from fastapi import APIRouter, HTTPException, Query
from src.schemas.catalog import ProductShortListResponse
from src.services.similar_products_service import similar_products_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Similar Products"])


@router.get("/products/{product_id}/similar", response_model=ProductShortListResponse)
def get_similar_products(
    product_id: str,
    category: str = Query(None, description="Category ID"),
    limit: int = Query(8, ge=1, le=20),
    offset: int = Query(0, ge=0),
):
    try:
        result = similar_products_service.get_similar_products(
            product_id=product_id,
            category_id=category,
            limit=limit,
            offset=offset
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Product not found"}
            )

        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"}
        )
