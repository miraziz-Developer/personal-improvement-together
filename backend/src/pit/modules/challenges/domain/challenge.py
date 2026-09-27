from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NotRequired, TypedDict, Unpack
from uuid import UUID

from pit.modules.challenges.domain.roadmap import Roadmap
from pit.modules.challenges.domain.schedule import Schedule
from pit.shared.domain.aggregate import AggregateRoot
from pit.shared.domain.errors import DomainError, InvalidStateTransition, InvariantViolation
from pit.shared.domain.money import Money

ALLOWED_DURATIONS = frozenset({7, 14, 21, 30, 60, 90})
MIN_STAKE = Money(10_000)
MAX_STAKE = Money(2_000_000)


class Category(StrEnum):
    SPORT = "sport"
    CODE = "code"
    STUDY = "study"
    READING = "reading"
    HEALTH = "health"
    CUSTOM = "custom"


class ProofType(StrEnum):
    PHOTO = "photo"
    TEXT = "text"
    GITHUB = "github"
    STRAVA = "strava"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ParticipationMode(StrEnum):
    FREE = "free"
    STAKE = "stake"


@dataclass(frozen=True, slots=True)
class StakePolicy:
    allowed: bool
    min_stake: Money = MIN_STAKE
    max_stake: Money = MAX_STAKE

    def __post_init__(self) -> None:
        if not MIN_STAKE <= self.min_stake <= self.max_stake <= MAX_STAKE:
            raise InvariantViolation("Garov chegaralari noto'g'ri")

    def validate(self, stake: Money) -> None:
        if not self.allowed:
            raise DomainError("Bu challenge'da pul qo'yish rejimi yo'q")
        if not self.min_stake <= stake <= self.max_stake:
            raise DomainError(f"Garov {self.min_stake} dan {self.max_stake} gacha bo'lishi kerak")


class ChallengeSpec(TypedDict):
    """What an author describes; status fields are decided by the factory methods."""

    title: str
    description: str
    category: Category
    duration_days: int
    difficulty: int
    proof_types: frozenset[ProofType]
    verification_prompt: str
    stake_policy: StakePolicy
    default_schedule: Schedule
    roadmap: NotRequired[Roadmap | None]


@dataclass(eq=False, kw_only=True)
class Challenge(AggregateRoot):
    """A challenge definition from the catalog (template or user-proposed)."""

    title: str
    description: str
    category: Category
    duration_days: int
    difficulty: int
    proof_types: frozenset[ProofType]
    verification_prompt: str
    stake_policy: StakePolicy
    default_schedule: Schedule  # the minimum a participant's own schedule is compared against
    is_template: bool
    approval_status: ApprovalStatus
    created_by: UUID | None = None
    roadmap: Roadmap | None = None  # what each week and working day is about

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise InvariantViolation("Challenge nomi bo'sh bo'lmasligi kerak")
        if self.duration_days not in ALLOWED_DURATIONS:
            raise InvariantViolation(
                f"Davomiylik {sorted(ALLOWED_DURATIONS)} kunlardan biri bo'lsin"
            )
        if not 1 <= self.difficulty <= 5:
            raise InvariantViolation("Qiyinlik 1 dan 5 gacha bo'lishi kerak")
        if not self.proof_types:
            raise InvariantViolation("Kamida bitta isbot turi kerak")
        if not self.verification_prompt.strip():
            raise InvariantViolation("AI uchun tekshiruv mezoni yozilishi kerak")

    @classmethod
    def create_template(cls, *, challenge_id: UUID, **spec: Unpack[ChallengeSpec]) -> Challenge:
        """Admin-made challenge: approved from the start."""
        return cls(
            id=challenge_id, is_template=True, approval_status=ApprovalStatus.APPROVED, **spec
        )

    @classmethod
    def propose(
        cls, *, challenge_id: UUID, created_by: UUID, **spec: Unpack[ChallengeSpec]
    ) -> Challenge:
        """User-made challenge: usable in free mode at once, stake mode only after moderation."""
        return cls(
            id=challenge_id,
            is_template=False,
            approval_status=ApprovalStatus.PENDING,
            created_by=created_by,
            **spec,
        )

    @classmethod
    def personal(
        cls, *, challenge_id: UUID, created_by: UUID, **spec: Unpack[ChallengeSpec]
    ) -> Challenge:
        """Built from an AI plan the user accepted. The AI wrote the criteria, so no moderation;
        stake mode is still protected by the schedule intensity rule."""
        return cls(
            id=challenge_id,
            is_template=False,
            approval_status=ApprovalStatus.APPROVED,
            created_by=created_by,
            **spec,
        )

    def approve(self) -> None:
        if self.approval_status is not ApprovalStatus.PENDING:
            raise InvalidStateTransition("Faqat ko'rib chiqilayotgan challenge tasdiqlanadi")
        self.approval_status = ApprovalStatus.APPROVED

    def reject(self) -> None:
        if self.approval_status is not ApprovalStatus.PENDING:
            raise InvalidStateTransition("Faqat ko'rib chiqilayotgan challenge rad etiladi")
        self.approval_status = ApprovalStatus.REJECTED

    def revise_from(self, template: Challenge) -> None:
        """Catalog upkeep: take the new texts, schedule and roadmap. Participations keep the
        schedule they joined with; the roadmap (what each day is about) follows at once."""
        if not self.is_template:
            raise InvalidStateTransition("Faqat katalog challenge'i yangilanadi")
        self.title, self.description = template.title, template.description
        self.default_schedule = template.default_schedule
        self.roadmap = template.roadmap

    def accepts(self, proof_type: ProofType) -> bool:
        return proof_type in self.proof_types

    def ensure_joinable(self, mode: ParticipationMode, stake: Money) -> None:
        if self.approval_status is ApprovalStatus.REJECTED:
            raise DomainError("Bu challenge rad etilgan")
        if mode is ParticipationMode.FREE:
            if not stake.is_zero:
                raise InvariantViolation("Oddiy rejimda garov bo'lmaydi")
            return
        if self.approval_status is not ApprovalStatus.APPROVED:
            # Otherwise anyone could stake money on a goal they defined as trivially easy.
            raise DomainError(
                "Pul qo'yish uchun challenge moderator tomonidan tasdiqlangan bo'lishi kerak"
            )
        self.stake_policy.validate(stake)

    def ensure_schedule_allowed(self, mode: ParticipationMode, schedule: Schedule) -> None:
        if mode is not ParticipationMode.STAKE:
            return  # free mode: any schedule the user wants
        schedule.ensure_stake_worthy()
        if not schedule.is_at_least_as_demanding_as(self.default_schedule):
            raise DomainError("Pulli rejimda reja challenge talabidan yengil bo'lishi mumkin emas")
