"""Together: friends doing one challenge with the same plan, invited by a link."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from pit.modules.challenges.domain.events import GroupMemberJoined
from pit.modules.challenges.domain.schedule import Schedule
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvariantViolation

MAX_GROUP_MEMBERS = 20  # beyond this "friends" become a crowd and the feed turns into noise
# No 0/O or 1/I/L: invite codes get read aloud and typed from screenshots.
INVITE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
INVITE_CODE_RE = re.compile(rf"^[{INVITE_ALPHABET}]{{8}}$")


@dataclass(eq=False, kw_only=True)
class Group(AggregateRoot):
    challenge_id: UUID
    owner_id: UUID
    invite_code: str
    schedule: Schedule  # everyone who joins follows the owner's plan
    created_at: datetime
    member_ids: list[UUID] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not INVITE_CODE_RE.fullmatch(self.invite_code):
            raise InvariantViolation("Taklif kodi noto'g'ri")

    @classmethod
    def create(
        cls,
        *,
        group_id: UUID,
        challenge_id: UUID,
        owner_id: UUID,
        invite_code: str,
        schedule: Schedule,
        created_at: datetime,
    ) -> Group:
        return cls(
            id=group_id,
            challenge_id=challenge_id,
            owner_id=owner_id,
            invite_code=invite_code,
            schedule=schedule,
            created_at=created_at,
            member_ids=[owner_id],
        )

    @property
    def is_full(self) -> bool:
        return len(self.member_ids) >= MAX_GROUP_MEMBERS

    def admit(self, user_id: UUID) -> None:
        if user_id in self.member_ids:
            raise DomainError("Siz allaqachon shu guruhdasiz")
        if self.is_full:
            raise DomainError(f"Guruh to'lgan ({MAX_GROUP_MEMBERS} kishi)")
        self.member_ids.append(user_id)
        self._record(
            GroupMemberJoined(group_id=self.id, user_id=user_id, challenge_id=self.challenge_id)
        )


def normalize_invite_code(code: str) -> str:
    return code.strip().upper()
