from typing import Protocol
from uuid import UUID

from pit.modules.challenges.domain.challenge import Challenge
from pit.modules.challenges.domain.group import Group
from pit.modules.challenges.domain.group_message import GroupMessage
from pit.modules.challenges.domain.participation import Participation


class ChallengeRepository(Protocol):
    def add(self, challenge: Challenge) -> None: ...

    async def get(self, challenge_id: UUID) -> Challenge | None: ...


class ParticipationRepository(Protocol):
    def add(self, participation: Participation) -> None: ...

    async def get(self, participation_id: UUID) -> Participation | None: ...

    async def has_open(self, user_id: UUID, challenge_id: UUID) -> bool: ...

    async def count_open_stakes(self, user_id: UUID) -> int: ...

    async def list_open_ids(self, user_id: UUID | None = None) -> list[UUID]: ...

    async def list_in_group(self, group_id: UUID) -> list[UUID]: ...


class GroupRepository(Protocol):
    def add(self, group: Group) -> None: ...

    async def get(self, group_id: UUID) -> Group | None: ...

    async def get_by_code(self, invite_code: str) -> Group | None: ...


class GroupMessageRepository(Protocol):
    """Append-only: a message is written once and read in order, never edited."""

    async def add(self, message: GroupMessage) -> None: ...

    async def recent(self, group_id: UUID, limit: int) -> list[GroupMessage]:
        """The newest `limit` messages, oldest first."""
        ...

    async def delete_for_user(self, user_id: UUID) -> None: ...
