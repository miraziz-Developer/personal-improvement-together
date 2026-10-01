"""The site opened inside Telegram (a Mini App) gets `initData` signed with the bot token —
Telegram vouches for who the user is, so no password is needed.
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app"""

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl

MAX_AGE = timedelta(days=1)  # Telegram re-signs on every launch; older data is a replay


class InvalidInitData(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramUser:
    id: int  # equals the private chat id with the bot
    username: str | None
    first_name: str
    language: str | None


def verify_init_data(init_data: str, bot_token: str, now: datetime) -> TelegramUser:
    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received = fields.pop("hash", "")
    if not received or not bot_token:
        raise InvalidInitData("unsigned")
    check = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise InvalidInitData("bad signature")
    try:
        signed_at = datetime.fromtimestamp(int(fields["auth_date"]), UTC)
        user = json.loads(fields["user"])
        found = TelegramUser(
            id=int(user["id"]),
            username=user.get("username"),
            first_name=str(user.get("first_name") or ""),
            language=user.get("language_code"),
        )
    except (KeyError, ValueError, TypeError):
        raise InvalidInitData("malformed") from None
    if now - signed_at > MAX_AGE:
        raise InvalidInitData("expired")
    return found
