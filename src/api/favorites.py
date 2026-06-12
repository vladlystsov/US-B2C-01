from fastapi import APIRouter, Depends, HTTPException, Query, Request
from src.schemas.favorite import FavoriteResponse
from src.services.favorites_service import FavoritesService
from src.database import get_db
from src.dependencies.auth import get_current_user_id
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/favorites", tags=["Favorites"])


@router.post("/{product_id}")
def add_to_favorites(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = FavoritesService(db)
    result = service.add_favorite(str(user_id), product_id)

    if result["status"] == "exists":
        return result

    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=201, content=result)


@router.delete("/{product_id}", status_code=204)
def remove_from_favorites(
    product_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    service = FavoritesService(db)
    service.remove_favorite(str(user_id), product_id)
    return None


@router.get("/", response_model=FavoriteResponse)
def get_favorites(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    service = FavoritesService(db)
    return service.get_favorites(str(user_id), limit=limit, offset=offset)
