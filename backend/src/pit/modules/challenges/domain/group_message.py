"""A short message in a friends' group ("keep going!", "done for today 💪")."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pit.shared.domain.errors import InvariantViolation

MAX_MESSAGE_LENGTH = 280


@dataclass(frozen=True, slots=True)
class GroupMessage:
    id: UUID
    group_id: UUID
    user_id: UUID
    text: str
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.text.strip() or len(self.text) > MAX_MESSAGE_LENGTH:
            raise InvariantViolation(f"Xabar 1-{MAX_MESSAGE_LENGTH} belgi bo'lsin")
