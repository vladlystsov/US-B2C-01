from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from src.schemas.category import CategoryTreeResponse, CategoryDetailResponse, BreadcrumbsResponse
from src.services.category_service import category_service

router = APIRouter(prefix="/api/v1", tags=["Categories"])


@router.get("/categories", response_model=CategoryTreeResponse)
def get_category_tree():
    try:
        result = category_service.get_category_tree()
        return result
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"}
        )


@router.get("/categories/{category_id}", response_model=CategoryDetailResponse)
def get_category_detail(
    category_id: str,
    include_product_count: bool = Query(False)
):
    try:
        result = category_service.get_category_detail(category_id, include_product_count)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "NOT_FOUND", "message": "Category not found"}
            )
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"}
        )


@router.get("/breadcrumbs", response_model=BreadcrumbsResponse)
def get_breadcrumbs(
    category_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
):
    result = category_service.get_breadcrumbs(category_id, product_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Not found"}
        )

    if result.get("error") == "ambiguous_param":
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_REQUEST", "message": "only one of category_id or product_id must be provided"}
        )

    if result.get("error") == "missing_param":
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_REQUEST", "message": "category_id or product_id must be provided"}
        )

    return result
