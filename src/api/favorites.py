from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from src.database import get_db
from src.dependencies.auth import get_current_user_id
from src.schemas.catalog import ProductShortListResponse
from src.services.favorites_service import FavoritesService

router = APIRouter(prefix="/api/v1/favorites", tags=["Favorites"])


@router.put("/{product_id}", status_code=204)
def add_to_favorites(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    FavoritesService(db).add_favorite(str(user_id), product_id)
    return Response(status_code=204)


@router.delete("/{product_id}", status_code=204)
def remove_from_favorites(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    FavoritesService(db).remove_favorite(str(user_id), product_id)
    return Response(status_code=204)


@router.get("", response_model=ProductShortListResponse)
def get_favorites(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return FavoritesService(db).get_favorites(str(user_id), limit=limit, offset=offset)
