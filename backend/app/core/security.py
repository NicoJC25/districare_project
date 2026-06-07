from hmac import compare_digest

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if x_api_key is None or not compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o ausente.",
        )
