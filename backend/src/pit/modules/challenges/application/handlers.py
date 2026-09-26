import secrets
from collections.abc import Callable
from datetime import date
from typing import Any, Protocol
from uuid import UUID, uuid4

from pit.modules.challenges.application.commands import (
    CancelParticipation,
    ChangeSchedule,
    CloseDays,
    CreateGroup,
    JoinChallenge,
    JoinGroup,
    RecordTaskApproved,
    RefreshDay,
)
from pit.modules.challenges.application.ports import DayEvidenceReader, StakeEscrow
from pit.modules.challenges.domain.challenge import Challenge, ParticipationMode
from pit.modules.challenges.domain.group import INVITE_ALPHABET, Group, normalize_invite_code
from pit.modules.challenges.domain.participation import (
    MAX_OPEN_STAKES,
    DayEvidence,
    DayStatus,
    Participation,
)
from pit.modules.challenges.domain.repositories import (
    ChallengeRepository,
    GroupRepository,
    ParticipationRepository,
)
from pit.modules.challenges.domain.schedule import Schedule
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.identity.domain.user import User
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.errors import DomainError, PermissionDenied
from pit.shared.domain.money import Money


class ChallengesUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...

    @property
    def challenges(self) -> ChallengeRepository: ...

    @property
    def participations(self) -> ParticipationRepository: ...

    @property
    def groups(self) -> GroupRepository: ...


type EscrowFactory = Callable[[Any], StakeEscrow]
type EvidenceReaderFactory = Callable[[Any], DayEvidenceReader]


async def start_participation(
    uow: ChallengesUoW,
    *,
    user: User,
    challenge: Challenge,
    mode: ParticipationMode,
    stake: Money,
    start_date: date,
    today: date,
    schedule: Schedule | None,
    escrow: EscrowFactory,
    stakes_enabled: bool,
    group_id: UUID | None = None,
) -> Participation:
    """Shared by both entry paths (catalog join and AI plan). Caller commits."""
    if mode is ParticipationMode.STAKE and not stakes_enabled:
        # Paid features are switched off until the platform grows; everything is free.
        raise DomainError("Pulli rejim hozircha yopiq — barcha challenge'lar bepul 🎁")
    if await uow.participations.has_open(user.id, challenge.id):
        raise DomainError("Siz bu challenge'da allaqachon qatnashyapsiz")
    if mode is ParticipationMode.STAKE:
        user.ensure_can_stake()
        if await uow.participations.count_open_stakes(user.id) >= MAX_OPEN_STAKES:
            raise DomainError(f"Bir vaqtda ko'pi bilan {MAX_OPEN_STAKES} ta pulli challenge")
    participation = Participation.start(
        participation_id=uuid4(),
        user_id=user.id,
        challenge=challenge,
        mode=mode,
        stake=stake,
        start_date=start_date,
        today=today,
        schedule=schedule,
        group_id=group_id,
    )
    uow.participations.add(participation)
    if participation.is_stake:
        # Same transaction: no participation without frozen money, no frozen money without it.
        await escrow(uow).lock(user_id=user.id, participation_id=participation.id, stake=stake)
    return participation


async def join_challenge(
    cmd: JoinChallenge,
    uow: ChallengesUoW,
    *,
    clock: Clock,
    escrow: EscrowFactory,
    stakes_enabled: bool = True,
) -> UUID:
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        challenge = require(await uow.challenges.get(cmd.challenge_id), "Challenge topilmadi")
        if not challenge.is_template and challenge.created_by != user.id:
            raise PermissionDenied(
                "Bu shaxsiy challenge — unga faqat taklif havolasi orqali qo'shilish mumkin"
            )
        today = local_date(clock.now(), user.timezone)
        participation = await start_participation(
            uow,
            user=user,
            challenge=challenge,
            mode=cmd.mode,
            stake=Money(cmd.stake_amount),
            start_date=cmd.start_date or today,
            today=today,
            schedule=cmd.schedule,
            escrow=escrow,
            stakes_enabled=stakes_enabled,
        )
        await uow.commit()
        return participation.id


async def _owned(uow: ChallengesUoW, participation_id: UUID, user_id: UUID) -> Participation:
    participation = require(await uow.participations.get(participation_id), "Challenge topilmadi")
    if participation.user_id != user_id:
        raise PermissionDenied("Bu sizning challenge'ingiz emas")
    return participation


async def cancel_participation(
    cmd: CancelParticipation, uow: ChallengesUoW, *, clock: Clock
) -> None:
    async with uow:
        participation = await _owned(uow, cmd.participation_id, cmd.user_id)
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        participation.cancel(local_date(clock.now(), user.timezone))
        await uow.commit()


async def change_schedule(cmd: ChangeSchedule, uow: ChallengesUoW, *, clock: Clock) -> None:
    async with uow:
        participation = await _owned(uow, cmd.participation_id, cmd.user_id)
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        participation.change_schedule(cmd.schedule, local_date(clock.now(), user.timezone))
        await uow.commit()


async def close_days(
    cmd: CloseDays, uow: ChallengesUoW, *, clock: Clock, evidence_reader: EvidenceReaderFactory
) -> None:
    async with uow:
        participation = require(
            await uow.participations.get(cmd.participation_id), "Challenge topilmadi"
        )
        if not participation.is_open:
            return
        user = require(await uow.users.get(participation.user_id), "Foydalanuvchi topilmadi")
        today = local_date(clock.now(), user.timezone)
        participation.activate(today)
        reader = evidence_reader(uow)
        for day in participation.days_to_settle(today):
            if not participation.is_open:
                break
            evidence = await reader.evidence_for(
                participation.id, day, participation.required_tasks(day)
            )
            participation.settle_day(day, evidence)
        await uow.commit()


async def _refresh(participation: Participation, day: date, reader: DayEvidenceReader) -> None:
    state = participation.day_status(day)
    if state not in (DayStatus.PENDING, DayStatus.AWAITING_REVIEW):
        return
    evidence = await reader.evidence_for(participation.id, day, participation.required_tasks(day))
    if state is DayStatus.AWAITING_REVIEW:
        # The day is over and was waiting for a verdict — judge it now.
        participation.settle_day(day, evidence)
    elif evidence is DayEvidence.APPROVED:
        # The day is still running: credit it as soon as every required task is approved.
        # Rejections wait for the deadline so the user can resubmit.
        participation.record_approved_day(day)


async def refresh_day(
    cmd: RefreshDay, uow: ChallengesUoW, *, evidence_reader: EvidenceReaderFactory
) -> None:
    async with uow:
        participation = require(
            await uow.participations.get(cmd.participation_id), "Challenge topilmadi"
        )
        await _refresh(participation, cmd.day, evidence_reader(uow))
        await uow.commit()


async def record_task_approved(
    cmd: RecordTaskApproved, uow: ChallengesUoW, *, evidence_reader: EvidenceReaderFactory
) -> None:
    async with uow:
        participation = require(
            await uow.participations.get(cmd.participation_id), "Challenge topilmadi"
        )
        participation.note_task_approved(cmd.day, cmd.task_key)
        await _refresh(participation, cmd.day, evidence_reader(uow))
        await uow.commit()


# --- together (groups) ---------------------------------------------------------------------


def new_invite_code() -> str:
    return "".join(secrets.choice(INVITE_ALPHABET) for _ in range(8))


async def create_group(cmd: CreateGroup, uow: ChallengesUoW, *, clock: Clock) -> str:
    async with uow:
        participation = await _owned(uow, cmd.participation_id, cmd.user_id)
        if participation.group_id is not None:
            group = require(await uow.groups.get(participation.group_id), "Guruh topilmadi")
            return group.invite_code
        group = Group.create(
            group_id=uuid4(),
            challenge_id=participation.challenge_id,
            owner_id=cmd.user_id,
            invite_code=new_invite_code(),  # a clash hits the unique index and is retried
            schedule=participation.current_schedule,
            created_at=clock.now(),
        )
        participation.attach_to_group(group.id)
        uow.groups.add(group)
        await uow.commit()
        return group.invite_code


async def join_group(
    cmd: JoinGroup,
    uow: ChallengesUoW,
    *,
    clock: Clock,
    escrow: EscrowFactory,
    stakes_enabled: bool = True,
) -> UUID:
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        group = require(
            await uow.groups.get_by_code(normalize_invite_code(cmd.invite_code)),
            "Taklif havolasi noto'g'ri yoki eskirgan",
        )
        challenge = require(await uow.challenges.get(group.challenge_id), "Challenge topilmadi")
        group.admit(user.id)
        today = local_date(clock.now(), user.timezone)
        participation = await start_participation(
            uow,
            user=user,
            challenge=challenge,
            mode=ParticipationMode.FREE,
            stake=Money.zero(),
            start_date=today,
            today=today,
            schedule=group.schedule,
            escrow=escrow,
            stakes_enabled=stakes_enabled,
            group_id=group.id,
        )
        await uow.commit()
        return participation.id
