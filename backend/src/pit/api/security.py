from datetime import datetime, timedelta
from uuid import UUID

import jwt

from pit.config import Settings

ALGORITHM = "HS256"


def issue_token(user_id: UUID, settings: Settings, now: datetime) -> str:
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_ttl_hours),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


SIGNUP_AUDIENCE = "google-signup"  # never accepted as a login token: read_token has no audience
SIGNUP_TTL = timedelta(minutes=30)


def issue_signup_token(
    google_sub: str, email: str | None, settings: Settings, now: datetime
) -> str:
    """Carries a verified Google identity from "sign in" to "finish your profile"."""
    payload = {
        "aud": SIGNUP_AUDIENCE,
        "gsub": google_sub,
        "email": email,
        "iat": now,
        "exp": now + SIGNUP_TTL,
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def read_signup_token(token: str, settings: Settings) -> tuple[str, str | None]:
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[ALGORITHM],
        audience=SIGNUP_AUDIENCE,
    )
    return str(payload["gsub"]), payload.get("email")


TELEGRAM_SIGNUP_AUDIENCE = "telegram-signup"


def issue_telegram_signup_token(chat_id: int, settings: Settings, now: datetime) -> str:
    """Carries a Telegram identity (checked from initData) to "finish your profile"."""
    payload = {"aud": TELEGRAM_SIGNUP_AUDIENCE, "tg": chat_id, "iat": now, "exp": now + SIGNUP_TTL}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def read_telegram_signup_token(token: str, settings: Settings) -> int:
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[ALGORITHM],
        audience=TELEGRAM_SIGNUP_AUDIENCE,
    )
    return int(payload["tg"])


SHARE_AUDIENCE = "share"


def issue_share_token(participation_id: UUID, settings: Settings) -> str:
    """A link the owner chose to share: it shows that one run's progress, and nothing else."""
    payload = {"aud": SHARE_AUDIENCE, "p": str(participation_id)}
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def read_share_token(token: str, settings: Settings) -> UUID:
    payload = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[ALGORITHM],
        audience=SHARE_AUDIENCE,
    )
    return UUID(str(payload["p"]))


def read_token(token: str, settings: Settings) -> UUID:
    """Raises jwt.PyJWTError / ValueError for anything invalid or expired."""
    payload = jwt.decode(token, settings.jwt_secret.get_secret_value(), algorithms=[ALGORITHM])
    return UUID(str(payload["sub"]))
