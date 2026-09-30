"""Public events of the challenges module. Wallet, verification and ranking react to these."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.shared.domain.events import DomainEvent
from pit.shared.domain.money import Money


@dataclass(frozen=True, kw_only=True)
class ParticipationStarted(DomainEvent):
    participation_id: UUID
    user_id: UUID
    challenge_id: UUID
    mode: ParticipationMode
    stake: Money


@dataclass(frozen=True, kw_only=True)
class ParticipationCancelled(DomainEvent):
    participation_id: UUID
    user_id: UUID
    mode: ParticipationMode
    stake: Money


@dataclass(frozen=True, kw_only=True)
class DayCompleted(DomainEvent):
    participation_id: UUID
    user_id: UUID
    day: date
    streak: int
    difficulty: int


@dataclass(frozen=True, kw_only=True)
class DayFrozen(DomainEvent):
    participation_id: UUID
    user_id: UUID
    day: date


@dataclass(frozen=True, kw_only=True)
class FreezeRegained(DomainEvent):
    """A long enough streak after a missed day gives the used freeze back."""

    participation_id: UUID
    user_id: UUID
    streak: int


@dataclass(frozen=True, kw_only=True)
class DayNeedsHumanReview(DomainEvent):
    """A stake day would be lost on an AI rejection alone — a moderator must decide."""

    participation_id: UUID
    day: date


@dataclass(frozen=True, kw_only=True)
class ParticipationCompleted(DomainEvent):
    participation_id: UUID
    user_id: UUID
    mode: ParticipationMode
    stake: Money
    difficulty: int
    duration_days: int
    finished_on: date


@dataclass(frozen=True, kw_only=True)
class ParticipationFailed(DomainEvent):
    participation_id: UUID
    user_id: UUID
    mode: ParticipationMode
    stake: Money
    missed_day: date


@dataclass(frozen=True, kw_only=True)
class OptionalTaskCompleted(DomainEvent):
    """Optional tasks don't decide the day — they only earn points."""

    participation_id: UUID
    user_id: UUID
    day: date
    task_key: str
    minutes: int


@dataclass(frozen=True, kw_only=True)
class ScheduleChanged(DomainEvent):
    participation_id: UUID
    effective_from: date


@dataclass(frozen=True, kw_only=True)
class GroupMemberJoined(DomainEvent):
    group_id: UUID
    user_id: UUID
    challenge_id: UUID
