from datetime import date, timedelta
from uuid import uuid4

import pytest

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.events import (
    DayNeedsHumanReview,
    ParticipationCompleted,
    ParticipationFailed,
)
from pit.modules.challenges.domain.participation import (
    DayEvidence,
    DayStatus,
    Participation,
    ParticipationStatus,
)
from pit.shared.domain.errors import DomainError, InvalidStateTransition, InvariantViolation
from pit.shared.domain.money import Money
from tests.factories import make_challenge

TODAY = date(2026, 10, 1)


def start(duration: int = 7, *, stake: int = 0, start_date: date = TODAY) -> Participation:
    return Participation.start(
        participation_id=uuid4(),
        user_id=uuid4(),
        challenge=make_challenge(duration_days=duration),
        mode=ParticipationMode.STAKE if stake else ParticipationMode.FREE,
        stake=Money(stake),
        start_date=start_date,
        today=TODAY,
    )


def test_one_freeze_per_ten_days() -> None:
    assert start(7).freezes_total == 0
    assert start(30).freezes_total == 3


def test_starts_active_today_or_scheduled_later() -> None:
    assert start().status is ParticipationStatus.ACTIVE
    assert start(start_date=TODAY + timedelta(days=2)).status is ParticipationStatus.SCHEDULED


def test_cannot_start_in_the_past() -> None:
    with pytest.raises(InvariantViolation):
        start(start_date=TODAY - timedelta(days=1))


def test_free_mode_cannot_carry_a_stake() -> None:
    with pytest.raises(InvariantViolation):
        Participation.start(
            participation_id=uuid4(),
            user_id=uuid4(),
            challenge=make_challenge(),
            mode=ParticipationMode.FREE,
            stake=Money(10_000),
            start_date=TODAY,
            today=TODAY,
        )


def test_stake_must_respect_challenge_limits() -> None:
    with pytest.raises(DomainError):
        start(stake=5_000)


def test_completing_every_day_completes_the_challenge() -> None:
    p = start(7)
    p.pull_events()
    for i in range(7):
        p.record_approved_day(TODAY + timedelta(days=i))
    assert p.status is ParticipationStatus.COMPLETED
    assert p.best_streak == 7
    assert any(isinstance(e, ParticipationCompleted) for e in p.pull_events())


def test_settling_is_idempotent() -> None:
    p = start(14)
    p.settle_day(TODAY, DayEvidence.NONE)
    p.settle_day(TODAY, DayEvidence.NONE)
    assert p.freezes_used == 1
    assert p.days[TODAY] is DayStatus.FROZEN


def test_ai_rejection_fails_free_mode_but_waits_for_human_in_stake_mode() -> None:
    free = start(7)
    free.settle_day(TODAY, DayEvidence.AI_REJECTED)
    assert free.status is ParticipationStatus.FAILED

    staked = start(7, stake=50_000)
    staked.pull_events()
    staked.settle_day(TODAY, DayEvidence.AI_REJECTED)
    assert staked.status is ParticipationStatus.ACTIVE
    assert staked.days[TODAY] is DayStatus.AWAITING_REVIEW
    assert [type(e) for e in staked.pull_events()] == [DayNeedsHumanReview]

    staked.settle_day(TODAY, DayEvidence.HUMAN_REJECTED)
    assert staked.status is ParticipationStatus.FAILED
    failed = [e for e in staked.pull_events() if isinstance(e, ParticipationFailed)]
    assert failed[0].stake == Money(50_000)


def test_pending_evidence_keeps_the_day_open() -> None:
    p = start(7)
    p.settle_day(TODAY, DayEvidence.PENDING)
    assert p.days[TODAY] is DayStatus.AWAITING_REVIEW
    p.settle_day(TODAY, DayEvidence.APPROVED)
    assert p.days[TODAY] is DayStatus.DONE


def test_cannot_prove_a_day_twice() -> None:
    p = start(7)
    p.record_approved_day(TODAY)
    with pytest.raises(DomainError):
        p.ensure_accepts_proof(TODAY, "main")


def test_cancel_only_before_start() -> None:
    scheduled = start(start_date=TODAY + timedelta(days=1))
    scheduled.cancel(TODAY)
    assert scheduled.status is ParticipationStatus.CANCELLED

    running = start()
    with pytest.raises(InvalidStateTransition):
        running.cancel(TODAY)
