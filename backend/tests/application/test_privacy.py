"""Erasing an account: every module forgets the person, statistics stay anonymous."""

from datetime import date

import pytest

from pit.modules.challenges.domain.participation import ParticipationStatus
from pit.modules.identity.application.commands import EraseAccount
from pit.modules.verification.infrastructure.storage import InMemoryStorage
from pit.shared.domain.errors import DomainError, InvalidStateTransition
from tests.application.conftest import World


async def test_erasing_forgets_the_person_everywhere(world: World) -> None:
    user = world.add_user()
    user.link_telegram(4242)
    user.connect_google("g-1", "ali@gmail.com")
    pid = await world.join(user, world.add_challenge())
    files = world.deps.files
    assert isinstance(files, InMemoryStorage)
    await files.put("proofs/photo.jpg", b"jpeg", "image/jpeg")
    await world.prove(user, pid)  # a photo proof, points, notifications
    assert world.leaderboard.boards and world.store.notifications

    await world.bus.handle(EraseAccount(user_id=user.id, confirm_username=user.username))

    assert user.is_erased and user.username.startswith("deleted_")
    assert (user.phone, user.telegram_chat_id, user.google_sub, user.email) == (None,) * 4
    assert user.birth_date == date(1998, 1, 1)  # only the cohort year survives
    (proof,) = world.store.proofs.values()
    assert (proof.file_key, proof.text_note, proof.phash) == (None, None, None)
    assert "proofs/photo.jpg" not in files.files
    assert not [n for n in world.store.notifications.values() if n.user_id == user.id]
    assert all(user.id not in board for board in world.leaderboard.boards.values())
    assert world.participation(pid).status is ParticipationStatus.CANCELLED
    assert world.participation(pid).days_completed == 1  # the anonymous statistic stays


async def test_the_username_must_be_typed_to_confirm(world: World) -> None:
    user = world.add_user()
    with pytest.raises(DomainError, match="username"):
        await world.bus.handle(EraseAccount(user_id=user.id, confirm_username="boshqa"))
    assert not user.is_erased


async def test_an_erased_account_cannot_be_erased_again(world: World) -> None:
    user = world.add_user()
    name = user.username
    await world.bus.handle(EraseAccount(user_id=user.id, confirm_username=name))
    with pytest.raises(DomainError):
        await world.bus.handle(EraseAccount(user_id=user.id, confirm_username=user.username))


async def test_a_running_stake_cannot_be_walked_away_from(world: World) -> None:
    user = world.add_user()
    await world.deposit(user, 100_000)
    pid = await world.join(user, world.add_challenge(), stake=50_000)
    with pytest.raises(InvalidStateTransition):
        world.participation(pid).withdraw(world.today)
