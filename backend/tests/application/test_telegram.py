"""The Telegram bot: linking, the coach's messages, and proofs sent from the chat."""

import pytest

from pit.modules.challenges.domain.challenge import ProofType
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.coaching.domain.messages import Moment
from pit.modules.identity.application.commands import IssueTelegramLink, RequestPasswordReset
from pit.modules.identity.domain.user import Locale, User
from pit.modules.telegram.application.bot import (
    PHONE_MENU,
    Callback,
    Label,
    TelegramBot,
    menu_for,
)
from pit.modules.telegram.application.common import html
from pit.modules.telegram.application.ports import Incoming
from pit.modules.telegram.application.texts import LABELS
from pit.modules.telegram.infrastructure.client import parse_update
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import AiDecision, ProofStatus
from tests.application.conftest import World
from tests.fakes import FakeConversation, FakeProofFiles, FakeUnitOfWork

CHAT = 7001

MAIN_MENU = menu_for("uz", "https://pit.uz")  # with the button that opens the app


@pytest.fixture
def files() -> FakeProofFiles:
    return FakeProofFiles()


@pytest.fixture
def bot(world: World, files: FakeProofFiles) -> TelegramBot:
    return TelegramBot(
        bus=world.bus,
        uow_factory=lambda: FakeUnitOfWork(world.store),
        api=world.telegram,
        conversation=FakeConversation(),
        files=files,
        clock=world.clock,
        code_secret=b"test-secret",
        web_url="https://pit.uz",
    )


async def say(bot: TelegramBot, text: str = "", chat: int = CHAT, **kwargs: str) -> None:
    await bot.handle(Incoming(chat_id=chat, text=text or None, **kwargs))


async def press(bot: TelegramBot, data: str, chat: int = CHAT) -> None:
    await bot.handle(Incoming(chat_id=chat, callback_id=f"cb-{data}", callback_data=data))


async def linked_user(
    world: World, bot: TelegramBot, chat: int = CHAT, *, phone: bool = True
) -> User:
    user = world.add_user(phone=phone)
    token: str = await world.bus.handle(IssueTelegramLink(user_id=user.id))
    await say(bot, f"/start {token}", chat)
    return user


def proofs(world: World) -> list[Proof]:
    return sorted(world.store.proofs.values(), key=lambda p: p.submitted_at)


# --- linking -------------------------------------------------------------------------------


async def test_start_link_connects_the_chat_once(world: World, bot: TelegramBot) -> None:
    user = world.add_user()
    token: str = await world.bus.handle(IssueTelegramLink(user_id=user.id))

    await say(bot, f"/start {token}")
    assert user.telegram_chat_id == CHAT
    assert user.username in world.telegram.last(CHAT).text

    await say(bot, f"/start {token}", chat=9999)  # a token works only once
    assert "eskirgan" in world.telegram.last(9999).text
    assert user.telegram_chat_id == CHAT


async def test_unknown_chat_is_invited_to_link(world: World, bot: TelegramBot) -> None:
    await say(bot, "/bugun")
    message = world.telegram.last(CHAT)
    assert "Ilovani ochish" in message.text  # the app opens right inside Telegram
    assert message.apps == ["https://pit.uz/tg?next=/profile"]


async def test_a_chat_follows_the_latest_account(world: World, bot: TelegramBot) -> None:
    first = await linked_user(world, bot)
    second = await linked_user(world, bot)
    assert (first.telegram_chat_id, second.telegram_chat_id) == (None, CHAT)


async def test_welcome_brings_the_button_menu(world: World, bot: TelegramBot) -> None:
    await linked_user(world, bot)
    assert world.telegram.last(CHAT).menu == MAIN_MENU


async def test_notifications_can_be_turned_off_from_settings(
    world: World, bot: TelegramBot
) -> None:
    user = await linked_user(world, bot)
    await say(bot, Label.SETTINGS)
    assert Callback.STOP_ASK in world.telegram.last(CHAT).callbacks

    await press(bot, Callback.STOP_ASK)  # asks first: a stray tap must not unlink
    assert user.telegram_chat_id == CHAT
    assert world.telegram.last(CHAT).callbacks == [Callback.STOP, Callback.CANCEL]

    await press(bot, Callback.STOP)
    assert user.telegram_chat_id is None
    assert world.telegram.last(CHAT).menu == []  # the menu disappears too


# --- the coach speaks through Telegram ------------------------------------------------------


async def test_coach_messages_reach_the_linked_chat(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    await world.join(user, world.add_challenge())

    (started,) = world.store.notifications.values()
    message = world.telegram.last(CHAT)
    assert message.text == f"<b>{html(started.title)}</b>\n\n{html(started.body)}"
    assert "today" in message.callbacks
    assert message.apps == ["https://pit.uz/tg?next=/routine"]


async def test_nothing_is_sent_to_users_without_telegram(world: World) -> None:
    await world.join(world.add_user(), world.add_challenge())
    assert world.store.notifications and not world.telegram.sent


async def test_blocked_bot_unlinks_the_chat(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    world.telegram.blocked.add(CHAT)
    await world.join(user, world.add_challenge())
    assert user.telegram_chat_id is None


async def test_telegram_outage_never_breaks_the_platform(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    world.telegram.down = True
    pid = await world.join(user, world.add_challenge())  # strict bus: would raise on failure
    await world.prove(user, pid)
    assert world.participation(pid).days_completed == 1


# --- proofs from the chat -------------------------------------------------------------------


async def test_today_then_photo_submits_a_proof(
    world: World, bot: TelegramBot, files: FakeProofFiles
) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())

    await say(bot, "/bugun")
    board = world.telegram.last(CHAT)
    assert "Sport zali" in board.text and "⬜" in board.text
    assert board.callbacks == [f"p:{pid.hex}:0"]

    await press(bot, f"p:{pid.hex}:0")
    assert "rasm yuboring" in world.telegram.last(CHAT).text
    assert world.telegram.answered == [f"cb-p:{pid.hex}:0"]

    await say(bot, photo_file_id="F1", caption="Bugun oyoq kuni")
    (proof,) = proofs(world)
    assert proof.task_key == "main" and proof.text_note == "Bugun oyoq kuni"
    assert proof.file_key in files.saved and proof.phash
    assert "qabul qilindi" in world.telegram.last(CHAT).text

    await world.run_worker()
    assert world.participation(pid).days_completed == 1
    day_done = [n for n in world.store.notifications.values() if n.moment is Moment.DAY_DONE]
    assert world.telegram.last(CHAT).text.startswith(f"<b>{html(day_done[0].title)}")


async def test_a_single_open_task_takes_the_photo_directly(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    await world.join(user, world.add_challenge())
    await say(bot, photo_file_id="F1")
    assert len(proofs(world)) == 1


async def test_photo_first_then_choose_the_task(world: World, bot: TelegramBot) -> None:
    schedule = Schedule.every_day(
        TaskSpec(key="run", title="Yugurish", minutes=30),
        TaskSpec(key="read", title="Kitob", minutes=20),
    )
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge(schedule=schedule))

    await say(bot, photo_file_id="F1")
    ask = world.telegram.last(CHAT)
    assert "Qaysi vazifa" in ask.text
    assert ask.callbacks == [f"p:{pid.hex}:0", f"p:{pid.hex}:1", Callback.CANCEL]
    assert not world.store.proofs

    await press(bot, f"p:{pid.hex}:1")
    (proof,) = proofs(world)
    assert proof.task_key == "read"

    await world.run_worker()  # one of two required tasks: a short "keep going" note
    assert "Yana 1 ta" in world.telegram.last(CHAT).text


async def test_text_proof_after_choosing_a_task(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())
    await say(bot, "salom")  # no task chosen yet
    assert Label.PROOF in world.telegram.last(CHAT).text

    await press(bot, f"p:{pid.hex}:0")
    await say(bot, "Bugun 1 soat shug'ullandim")
    (proof,) = proofs(world)
    assert proof.text_note == "Bugun 1 soat shug'ullandim" and proof.file_key is None


async def test_photo_only_challenge_refuses_text(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    challenge = world.add_challenge(proof_types=frozenset({ProofType.PHOTO}))
    pid = await world.join(user, challenge)
    await press(bot, f"p:{pid.hex}:0")
    await say(bot, "rasm yo'q")
    assert "rasm kerak" in world.telegram.last(CHAT).text
    assert not world.store.proofs


async def test_approved_task_leaves_the_board(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())
    await world.prove(user, pid)
    await say(bot, "/bugun")
    board = world.telegram.last(CHAT)
    assert "✅ Sport zali" in board.text and not board.callbacks


async def test_someone_elses_participation_is_refused(world: World, bot: TelegramBot) -> None:
    other = world.add_user()
    pid = await world.join(other, world.add_challenge())
    await linked_user(world, bot)
    await press(bot, f"p:{pid.hex}:0")
    assert "topilmadi" in world.telegram.last(CHAT).text
    assert not world.store.proofs


async def test_status_shows_streaks(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())
    await world.prove(user, pid)
    await say(bot, "/holat")
    assert "Streak: 1 kun" in world.telegram.last(CHAT).text


async def test_rejected_proof_can_be_sent_again(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())
    world.verifier.will_return(AiDecision.REJECT, confidence=0.97, reason="Rasm xira")
    await say(bot, photo_file_id="F1")
    await world.run_worker()
    assert proofs(world)[0].status is ProofStatus.REJECTED

    await say(bot, "/bugun")
    assert world.telegram.last(CHAT).callbacks == [f"p:{pid.hex}:0"]


# --- parsing Telegram updates ---------------------------------------------------------------


def test_parse_update_keeps_private_chats_and_the_largest_photo() -> None:
    private = {"id": 5, "type": "private"}
    photo = {"message": {"chat": private, "photo": [{"file_id": "s"}, {"file_id": "L"}]}}
    assert parse_update(photo) == Incoming(chat_id=5, photo_file_id="L")

    group = {"message": {"chat": {"id": -1, "type": "group"}, "text": "/bugun"}}
    assert parse_update(group) is None

    query = {"callback_query": {"id": "q", "data": "today", "message": {"chat": private}}}
    assert parse_update(query) == Incoming(chat_id=5, callback_id="q", callback_data="today")

    document = {
        "message": {"chat": private, "document": {"file_id": "D", "mime_type": "image/png"}}
    }
    assert parse_update(document) == Incoming(chat_id=5, photo_file_id="D")


# --- the button menu ------------------------------------------------------------------------


async def test_proof_button_with_one_open_task_asks_right_away(
    world: World, bot: TelegramBot
) -> None:
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge())
    await say(bot, Label.PROOF)
    assert "Sport zali" in world.telegram.last(CHAT).text
    assert world.telegram.last(CHAT).callbacks == [Callback.CANCEL]

    await say(bot, photo_file_id="F1")
    (proof,) = proofs(world)
    assert proof.participation_id == pid


async def test_proof_button_with_several_tasks_offers_a_choice(
    world: World, bot: TelegramBot
) -> None:
    schedule = Schedule.every_day(
        TaskSpec(key="run", title="Yugurish", minutes=30),
        TaskSpec(key="read", title="Kitob", minutes=20),
    )
    user = await linked_user(world, bot)
    pid = await world.join(user, world.add_challenge(schedule=schedule))
    await say(bot, Label.PROOF)
    assert world.telegram.last(CHAT).callbacks == [
        f"p:{pid.hex}:0",
        f"p:{pid.hex}:1",
        Callback.CANCEL,
    ]


async def test_cancel_forgets_the_chosen_task(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    await world.join(user, world.add_challenge())
    await say(bot, Label.PROOF)
    await press(bot, Callback.CANCEL)
    await say(bot, "Bugun 1 soat shug'ullandim")  # no longer taken as a proof
    assert not world.store.proofs
    assert Label.PROOF in world.telegram.last(CHAT).text


async def test_menu_buttons_are_never_taken_as_text_proofs(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    await world.join(user, world.add_challenge())
    await say(bot, Label.PROOF)  # waiting for a proof...
    await say(bot, Label.STATUS)  # ...but the user taps another button
    assert not world.store.proofs
    assert "Natijalaringiz" in world.telegram.last(CHAT).text


# --- phone verification through Telegram (instead of SMS) -----------------------------------


async def contact(bot: TelegramBot, phone: str, *, own: bool = True) -> None:
    await bot.handle(Incoming(chat_id=CHAT, contact_phone=phone, contact_is_own=own))


async def test_new_link_offers_phone_verification(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot, phone=False)
    assert world.telegram.last(CHAT).menu == PHONE_MENU

    await contact(bot, "998901234567")
    assert user.phone_verified and user.phone == "+998901234567"
    assert world.telegram.last(CHAT).menu == menu_for(
        "uz", "https://pit.uz"
    )  # back to the normal buttons
    assert not world.sms.sent  # no SMS was needed


async def test_someone_elses_contact_does_not_verify(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot, phone=False)
    await contact(bot, "998901234567", own=False)
    assert not user.phone_verified


async def test_later_brings_the_menu_back(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot, phone=False)
    await say(bot, Label.LATER)
    assert world.telegram.last(CHAT).menu == MAIN_MENU and not user.phone_verified


async def test_website_deep_link_and_settings_ask_for_the_phone(
    world: World, bot: TelegramBot
) -> None:
    await linked_user(world, bot, phone=False)
    await say(bot, "/start phone")
    assert world.telegram.last(CHAT).menu == PHONE_MENU

    await say(bot, Label.SETTINGS)
    assert Callback.PHONE in world.telegram.last(CHAT).callbacks


async def test_password_reset_code_goes_to_telegram(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    await world.bus.handle(RequestPasswordReset(username=user.username))
    assert "parolni tiklash kodi" in world.telegram.last(CHAT).text
    assert not world.sms.sent


async def test_password_reset_falls_back_to_sms(world: World, bot: TelegramBot) -> None:
    user = await linked_user(world, bot)
    world.telegram.down = True
    await world.bus.handle(RequestPasswordReset(username=user.username))
    assert world.sms.sent


# --- the bot in Russian ----------------------------------------------------------------------


async def test_a_russian_speaker_gets_a_russian_bot(world: World, bot: TelegramBot) -> None:
    user = world.add_user()
    user.change_locale(Locale.RU)
    token: str = await world.bus.handle(IssueTelegramLink(user_id=user.id))
    await say(bot, f"/start {token}")
    welcome = world.telegram.last(CHAT)
    assert "Telegram подключён" in welcome.text
    assert welcome.menu == menu_for("ru", "https://pit.uz")

    await world.join(user, world.add_challenge())
    await say(bot, LABELS["ru"]["today"])
    assert "<b>Сегодня</b>" in world.telegram.last(CHAT).text
    await say(bot, Label.TODAY)  # an old Uzbek keyboard still works after switching
    assert "<b>Сегодня</b>" in world.telegram.last(CHAT).text


async def test_a_stranger_is_greeted_in_their_telegram_language(
    world: World, bot: TelegramBot
) -> None:
    await bot.handle(Incoming(chat_id=CHAT, text="/start", language="ru"))
    assert "коуч PIT" in world.telegram.last(CHAT).text
