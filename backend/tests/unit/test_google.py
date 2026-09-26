"""GoogleIdTokenVerifier with a locally generated key standing in for Google's."""

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from pit.modules.identity.infrastructure.google import GoogleIdTokenVerifier
from pit.shared.domain.errors import DomainError

CLIENT_ID = "ours.apps.googleusercontent.com"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _Keys:
    def get_signing_key_from_jwt(self, token: str) -> Any:
        return jwt.PyJWK.from_dict(
            {**jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True), "alg": "RS256"}
        )


def token(**overrides: object) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "1234567890",
        "email": "ali@gmail.com",
        "email_verified": True,
        "iat": now,
        "exp": now + 600,
        **overrides,
    }
    return jwt.encode(claims, KEY, algorithm="RS256")


@pytest.fixture
def verifier() -> GoogleIdTokenVerifier:
    verifier = GoogleIdTokenVerifier(CLIENT_ID)
    verifier._keys = _Keys()  # type: ignore[assignment]
    return verifier


async def test_a_valid_token_gives_the_identity(verifier: GoogleIdTokenVerifier) -> None:
    identity = await verifier.verify(token())
    assert (identity.sub, identity.email) == ("1234567890", "ali@gmail.com")


@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "another-app.apps.googleusercontent.com"},  # issued for someone else
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 60},
        {"email_verified": False},
    ],
)
async def test_untrustworthy_tokens_are_refused(
    verifier: GoogleIdTokenVerifier, overrides: dict[str, object]
) -> None:
    with pytest.raises(DomainError):
        await verifier.verify(token(**overrides))


async def test_a_token_signed_by_another_key_is_refused(verifier: GoogleIdTokenVerifier) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(jwt.decode(token(), options={"verify_signature": False}), other, "RS256")
    with pytest.raises(DomainError):
        await verifier.verify(forged)
