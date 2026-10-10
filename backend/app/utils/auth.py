from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings


security = HTTPBearer(
    auto_error=True,
)


@lru_cache
def get_jwks_client() -> PyJWKClient:
    """Create a cached JWKS client for Supabase."""

    jwks_url = (
        f"{settings.supabase_url}"
        "/auth/v1/.well-known/jwks.json"
    )

    return PyJWKClient(jwks_url)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
) -> dict:
    """
    Verify a Supabase JWT and return its claims.
    """

    token = credentials.credentials

    try:
        jwks_client = get_jwks_client()

        signing_key = (
            jwks_client.get_signing_key_from_jwt(token)
        )

        algorithm = signing_key.algorithm_name

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        ) from exc

    user_id = claims.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has no user ID.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return claims