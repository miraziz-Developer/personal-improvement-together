from dataclasses import dataclass
from datetime import date
from uuid import UUID

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.schedule import Schedule
from pit.shared.application.messagebus import Command


@dataclass(frozen=True, kw_only=True)
class JoinChallenge(Command):
    """The "pick a ready-made challenge" path (the other path is planning.StartPlan)."""

    user_id: UUID
    challenge_id: UUID
    mode: ParticipationMode
    stake_amount: int = 0
    start_date: date | None = None  # default: today in the user's timezone
    schedule: Schedule | None = None  # default: the challenge's own schedule


@dataclass(frozen=True, kw_only=True)
class CancelParticipation(Command):
    user_id: UUID
    participation_id: UUID


@dataclass(frozen=True, kw_only=True)
class ChangeSchedule(Command):
    user_id: UUID
    participation_id: UUID
    schedule: Schedule


@dataclass(frozen=True, kw_only=True)
class CloseDays(Command):
    """Daily job, one per open participation: activate, then judge every day that has ended."""

    participation_id: UUID


@dataclass(frozen=True, kw_only=True)
class RefreshDay(Command):
    """Evidence for a day changed (AI or moderator decided) — re-check that day."""

    participation_id: UUID
    day: date


@dataclass(frozen=True, kw_only=True)
class RecordTaskApproved(Command):
    """A proof for one task was approved: award optional tasks, then re-check the day."""

    participation_id: UUID
    day: date
    task_key: str


@dataclass(frozen=True, kw_only=True)
class CreateGroup(Command):
    """Owner invites friends to their participation. Idempotent; returns the invite code."""

    user_id: UUID
    participation_id: UUID


@dataclass(frozen=True, kw_only=True)
class JoinGroup(Command):
    """A friend follows the invite link: same challenge, same plan, starting today."""

    user_id: UUID
    invite_code: str


@dataclass(frozen=True, kw_only=True)
class LeaveChallenge(Command):
    """Stop a free challenge for good (a stake run cannot be left)."""

    user_id: UUID
    participation_id: UUID


@dataclass(frozen=True, kw_only=True)
class PauseChallenge(Command):
    """A break of a few days; the run gets that much longer. Returns the first paused day."""

    user_id: UUID
    participation_id: UUID
    days: int


@dataclass(frozen=True, kw_only=True)
class PostGroupMessage(Command):
    """A short message to the friends' group of this participation."""

    user_id: UUID
    participation_id: UUID
    text: str
