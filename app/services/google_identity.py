"""Google ID token (Google Identity Services) tekshiruvi.

Frontend Google'dan `credential` (RS256 imzolangan JWT) oladi va bizga yuboradi.
Tokenga mijoz tomonidan ishonib bo'lmaydi — imzo Google'ning ochiq kalitlari
(JWKS) bilan, `aud` bizning Client ID bilan, `iss` Google bilan tekshiriladi.
Aks holda istalgan odam o'zi yasagan token bilan istalgan email nomidan kiradi.
"""

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, status

from app.core.config import settings

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = frozenset({"accounts.google.com", "https://accounts.google.com"})


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str | None
    picture: str | None


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    # PyJWKClient kalitlarni keshlaydi — har kirishda Google'ga so'rov ketmaydi.
    return jwt.PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True, lifespan=3600, timeout=10)


def _invalid() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Google credential",
    )


def verify_google_id_token(credential: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(credential)
        claims = jwt.decode(
            credential,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.google_client_id,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is temporarily unavailable",
        ) from exc
    except jwt.PyJWTError as exc:
        raise _invalid() from exc

    # PyJWT `issuer` faqat bitta qiymat qabul qiladi, Google esa ikkalasini ishlatadi.
    if claims.get("iss") not in GOOGLE_ISSUERS or not claims.get("email"):
        raise _invalid()

    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(claims["email"]),
        email_verified=claims.get("email_verified") is True,
        name=claims.get("name"),
        picture=claims.get("picture"),
    )
