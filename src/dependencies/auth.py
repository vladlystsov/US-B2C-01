from fastapi import Depends, HTTPException, Request, Header
from jose import JWTError, jwt
from uuid import UUID
from typing import Optional
from src.config import settings


async def get_current_user_id(request: Request) -> UUID:
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Missing Authorization header"}
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid authorization scheme"}
        )

    token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id_str = payload.get("sub")

        if not user_id_str:
            raise HTTPException(
                status_code=401,
                detail={"code": "UNAUTHORIZED", "message": "Token missing 'sub' claim"}
            )

        return UUID(user_id_str)

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid or expired token"}
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Invalid user_id format in token"}
        )


def verify_service_key(x_service_key: Optional[str] = Header(None)):
    if not x_service_key or x_service_key != settings.B2B_SERVICE_KEY:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_SERVICE_KEY", "message": "Invalid X-Service-Key header"}
        )
    return True
