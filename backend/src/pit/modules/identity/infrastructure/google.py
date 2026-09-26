"""Verifies "Sign in with Google" ID tokens against Google's published signing keys."""

import asyncio

import jwt

from pit.modules.identity.application.ports import GoogleIdentity
from pit.shared.domain.errors import DomainError

GOOGLE_KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")


class GoogleIdTokenVerifier:
    def __init__(self, client_id: str) -> None:
        self._client_id = client_id
        # Caches Google's keys; they rotate every few days and are refetched on a new "kid".
        self._keys = jwt.PyJWKClient(GOOGLE_KEYS_URL, cache_keys=True, lifespan=6 * 3600)

    async def verify(self, credential: str) -> GoogleIdentity:
        try:
            key = await asyncio.to_thread(self._keys.get_signing_key_from_jwt, credential)
            claims = jwt.decode(
                credential,
                key.key,
                algorithms=["RS256"],
                audience=self._client_id,  # issued for our site, not another app
                issuer=GOOGLE_ISSUERS,
                options={"require": ["sub", "exp", "iat"]},
            )
        except jwt.PyJWKClientConnectionError:
            raise DomainError("Google bilan aloqa yo'q. Birozdan so'ng urinib ko'ring") from None
        except jwt.PyJWTError:
            raise DomainError("Google orqali kirish amalga oshmadi. Qayta urinib ko'ring") from None
        if not claims.get("email_verified", False):
            raise DomainError("Google akkauntingizdagi email tasdiqlanmagan")
        return GoogleIdentity(
            sub=str(claims["sub"]), email=claims.get("email"), name=claims.get("name")
        )
