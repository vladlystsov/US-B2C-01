from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.schemas.category import CategoryItem, CategoryTreeNode
from src.services.category_service import OrphanCategoryError, category_service

router = APIRouter(prefix="/api/v1/catalog", tags=["Categories"])


@router.get("/categories", response_model=list[CategoryItem])
def get_categories():
    try:
        return category_service.get_categories()
    except OrphanCategoryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CATEGORY_TREE", "message": str(exc)})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})


@router.get("/categories/tree", response_model=list[CategoryTreeNode])
def get_category_tree():
    try:
        return category_service.get_category_tree()
    except OrphanCategoryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CATEGORY_TREE", "message": str(exc)})
    except Exception:
        raise HTTPException(status_code=502, detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"})


@router.get("/breadcrumbs", response_model=list[CategoryItem], include_in_schema=False)
def get_breadcrumbs(category_id: Optional[str] = Query(None), product_id: Optional[str] = Query(None)):
    try:
        result = category_service.get_breadcrumbs(category_id, product_id)
    except OrphanCategoryError as exc:
        raise HTTPException(status_code=422, detail={"code": "INVALID_CATEGORY_TREE", "message": str(exc)})
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Not found"})
    if isinstance(result, dict):
        if result["error"] == "ambiguous_param":
            message = "only one of category_id or product_id must be provided"
        else:
            message = "category_id or product_id must be provided"
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": message})
    return result
