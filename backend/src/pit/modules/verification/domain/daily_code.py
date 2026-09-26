"""Per-day anti-cheat code the user must show in the photo (e.g. written on paper).

Derived with HMAC from a server secret, so it needs no storage and cannot be guessed ahead.
"""

import hashlib
import hmac
from datetime import date
from uuid import UUID

# No 0/O or 1/I — easy to read from a handwritten note. 32 symbols keep the mapping unbiased.
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 4


def daily_code(secret: bytes, participation_id: UUID, day: date) -> str:
    message = f"{participation_id}:{day.isoformat()}".encode()
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return "".join(ALPHABET[b % len(ALPHABET)] for b in digest[:CODE_LENGTH])
