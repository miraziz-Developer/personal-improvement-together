"""The conversational side of the bot: link the account, show today's tasks, take proofs.

Reads go through a unit of work; every change goes through the message bus, exactly like the
website — the bot is just another front door to the same use cases."""

from __future__ import annotations

import logging
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from pit.modules.challenges.domain.challenge import Challenge, ProofType
from pit.modules.challenges.domain.participation import Participation, ParticipationStatus
from pit.modules.challenges.domain.schedule import TaskSpec
from pit.modules.coaching.application.commands import CheerFriend
from pit.modules.coaching.application.ports import ChallengeTexts, OwnTexts
from pit.modules.identity.application.commands import (
    LinkTelegram,
    UnlinkTelegram,
    VerifyPhoneFromTelegram,
)
from pit.modules.identity.domain.user import User
from pit.modules.telegram.application.common import (
    CHEER_CALLBACK,
    TODAY_CALLBACK,
    TelegramUoW,
    html,
    human_date,
    keyboard,
    site_row,
)
from pit.modules.telegram.application.ports import (
    Button,
    Conversation,
    Incoming,
    Keyboard,
    Menu,
    ProofFiles,
    ShareContact,
    TelegramApi,
    TelegramUnavailable,
)
from pit.modules.telegram.application.texts import LABELS, label, label_action, pick, tr
from pit.modules.verification.application.commands import SubmitProof
from pit.modules.verification.domain.daily_code import daily_code
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import ProofStatus
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.errors_i18n import translate_error
from pit.shared.application.messagebus import MessageBus
from pit.shared.domain.errors import DomainError

logger = logging.getLogger(__name__)

PROOF_CALLBACK = "p"  # p:<participation hex>:<task index> — fits Telegram's 64-byte limit


# The persistent menu under the input field — the bot is driven by these, not by commands.
class Label:
    """Uzbek button texts (the default language); see texts.LABELS for all languages."""

    TODAY = LABELS["uz"]["today"]
    PROOF = LABELS["uz"]["proof"]
    STATUS = LABELS["uz"]["status"]
    SETTINGS = LABELS["uz"]["settings"]
    LATER = LABELS["uz"]["later"]


def menu_for(locale: str) -> Menu:
    return [
        [label(locale, "today"), label(locale, "proof")],
        [label(locale, "status"), label(locale, "settings")],
    ]


def phone_menu_for(locale: str) -> Menu:
    return [[ShareContact(label(locale, "share_phone"))], [label(locale, "later")]]


MENU: Menu = menu_for("uz")
PHONE_MENU: Menu = phone_menu_for("uz")
PHONE_DEEP_LINK = "phone"  # t.me/<bot>?start=phone — from the website's phone card


class Callback:
    TODAY = TODAY_CALLBACK
    HELP = "help"
    CANCEL = "cancel"
    STOP_ASK = "stop?"
    STOP = "stop!"
    PHONE = "phone"


def cancel_row(locale: str) -> list[Button]:
    return [Button(tr(locale, "cancel"), callback=Callback.CANCEL)]


def help_text(locale: str) -> str:
    return tr(
        locale,
        "help",
        today=label(locale, "today"),
        proof=label(locale, "proof"),
        status=label(locale, "status"),
        settings=label(locale, "settings"),
    )


STATUS_ICON = {
    ProofStatus.APPROVED: ("✅", ""),
    ProofStatus.PENDING: ("⏳", "checking"),
    ProofStatus.NEEDS_REVIEW: ("👀", "in_review"),
    ProofStatus.REJECTED: ("❌", "rejected"),
}


@dataclass(frozen=True, slots=True)
class _Open:
    """A task that can take a proof right now."""

    participation: Participation
    challenge: Challenge
    task: TaskSpec
    index: int  # position in today's plan; short enough for callback data


class TelegramBot:
    def __init__(
        self,
        *,
        bus: MessageBus,
        uow_factory: Callable[[], TelegramUoW],
        api: TelegramApi,
        conversation: Conversation,
        files: ProofFiles,
        clock: Clock,
        code_secret: bytes,
        web_url: str,
        texts: ChallengeTexts | None = None,
    ) -> None:
        self._texts: ChallengeTexts = texts or OwnTexts()
        self._bus = bus
        self._uow = uow_factory
        self._api = api
        self._conversation = conversation
        self._files = files
        self._clock = clock
        self._code_secret = code_secret
        self._web_url = web_url

    async def handle(self, message: Incoming) -> None:
        try:
            await self._route(message)
        except DomainError as error:
            user = await self._user(message.chat_id)
            lang = user.locale.value if user else pick(message.language)
            await self._say(message.chat_id, f"⚠️ {html(translate_error(error.message, lang))}")
        finally:
            if message.callback_id:  # stops the spinner on the pressed button
                with suppress(TelegramUnavailable):
                    await self._api.answer_callback(message.callback_id)

    # --- routing ---------------------------------------------------------------------------

    async def _route(self, message: Incoming) -> None:
        chat_id = message.chat_id
        text = (message.text or "").strip()
        guest = pick(message.language)  # Telegram's app language, until we know the user
        if text.startswith("/start"):
            await self._start(chat_id, text.removeprefix("/start").strip(), guest)
            return
        user = await self._user(chat_id)
        if user is None:
            await self._not_linked(chat_id, guest)
            return
        if message.callback_data:
            await self._callback(user, chat_id, message.callback_data)
        elif message.contact_phone is not None:
            await self._contact(user, chat_id, message.contact_phone, message.contact_is_own)
        elif message.photo_file_id:
            await self._photo(user, chat_id, message.photo_file_id, message.caption)
        elif not await self._menu(user, chat_id, text) and text:
            await self._text(user, chat_id, text)

    async def _menu(self, user: User, chat_id: int, text: str) -> bool:
        """Menu buttons (and their old command names). Returns False for anything else."""
        lang = user.locale.value
        command = text.split()[0].split("@")[0].lower() if text.startswith("/") else text
        match label_action(text) or command:
            case "today" | "/bugun" | "/today":
                await self._conversation.clear(chat_id)  # changed their mind: start over
                await self._today(user, chat_id)
            case "proof":
                await self._conversation.clear(chat_id)
                await self._pick_task(user, chat_id)
            case "status" | "/holat" | "/status":
                await self._status(user, chat_id)
            case "settings" | "/stop":
                await self._settings(user, chat_id)
            case "later":
                later = tr(lang, "later_ok", settings=label(lang, "settings"))
                await self._say(chat_id, later, menu=menu_for(lang))
            case _ if text.startswith("/"):
                await self._say(chat_id, help_text(lang), menu=menu_for(lang))
            case _:
                return False
        return True

    async def _start(self, chat_id: int, token: str, guest: str) -> None:
        if token == PHONE_DEEP_LINK:
            user = await self._user(chat_id)
            if user is None:
                await self._not_linked(chat_id, guest)
            elif user.phone_verified:
                lang = user.locale.value
                done = tr(lang, "phone_already", phone=user.phone)
                await self._say(chat_id, done, menu=menu_for(lang))
            else:
                await self._ask_phone(chat_id, user.locale.value)
            return
        if token:
            user_id: UUID = await self._bus.handle(LinkTelegram(token=token, chat_id=chat_id))
            uow = self._uow()
            async with uow:
                user = await uow.users.get(user_id)
            lang = user.locale.value if user else guest
            name = html(user.username) if user else ""
            await self._say(chat_id, tr(lang, "welcome", name=name), menu=menu_for(lang))
            if user is not None and not user.phone_verified:
                await self._ask_phone(chat_id, lang)
            return
        linked = await self._user(chat_id)
        if linked is not None:
            lang = linked.locale.value
            again = tr(lang, "already_linked", help=help_text(lang))
            await self._say(chat_id, again, menu=menu_for(lang))
        else:
            await self._not_linked(chat_id, guest)

    async def _not_linked(self, chat_id: int, lang: str) -> None:
        site = keyboard(site_row(self._web_url, "/profile", tr(lang, "btn_site")))
        # Without a site button there is room to hide a menu left from an earlier link.
        await self._say(chat_id, tr(lang, "not_linked"), site, menu=None if site else [])

    async def _callback(self, user: User, chat_id: int, data: str) -> None:
        lang = user.locale.value
        match data:
            case Callback.TODAY:
                await self._today(user, chat_id)
                return
            case Callback.HELP:
                await self._say(chat_id, help_text(lang), menu=menu_for(lang))
                return
            case Callback.PHONE:
                await self._ask_phone(chat_id, lang)
                return
            case Callback.CANCEL:
                await self._conversation.clear(chat_id)
                await self._say(chat_id, tr(lang, "cancelled"))
                return
            case Callback.STOP_ASK:
                await self._say(
                    chat_id,
                    tr(lang, "stop_ask"),
                    [
                        [
                            Button(tr(lang, "stop_yes"), callback=Callback.STOP),
                            Button(tr(lang, "stop_no"), callback=Callback.CANCEL),
                        ]
                    ],
                )
                return
            case Callback.STOP:
                await self._bus.handle(UnlinkTelegram(chat_id=chat_id))
                await self._conversation.clear(chat_id)
                await self._say(chat_id, tr(lang, "stopped"), menu=[])
                return
        if data.startswith(f"{CHEER_CALLBACK}:"):
            await self._cheer(user, chat_id, data.removeprefix(f"{CHEER_CALLBACK}:"))
            return
        parts = data.split(":", 2)
        if len(parts) != 3 or parts[0] != PROOF_CALLBACK:
            return
        try:
            participation_id, index = UUID(hex=parts[1]), int(parts[2])
        except ValueError:
            return
        target = await self._open_task(user, participation_id, index)
        held_photo = (await self._conversation.get(chat_id)).get("photo")
        if held_photo and target.challenge.accepts(ProofType.PHOTO):
            await self._submit(user, chat_id, target, file_id=held_photo)
            return
        await self._choose(user, chat_id, target)

    async def _cheer(self, user: User, chat_id: int, notification_hex: str) -> None:
        try:
            notification_id = UUID(hex=notification_hex)
        except ValueError:
            return
        uow = self._uow()
        async with uow:
            notification = await uow.notifications.get(notification_id)
            if (
                notification is None
                or notification.user_id != user.id
                or notification.subject_id is None
                or notification.participation_id is None
            ):
                return
            friend = await uow.users.get(notification.subject_id)
        if friend is None or friend.is_erased:
            return
        await self._bus.handle(
            CheerFriend(
                user_id=user.id,
                participation_id=notification.participation_id,
                friend_username=friend.username,
            )
        )
        await self._say(chat_id, tr(user.locale.value, "cheered", name=html(friend.username)))

    async def _choose(self, user: User, chat_id: int, target: _Open) -> None:
        """Remember the task; the next photo or text the user sends proves it."""
        await self._conversation.update(
            chat_id, participation=target.participation.id.hex, task=target.task.key
        )
        await self._say(chat_id, self._ask_for_proof(user, target), [cancel_row(user.locale.value)])

    async def _pick_task(self, user: User, chat_id: int) -> None:
        lang = user.locale.value
        open_tasks = await self._open_tasks(user)
        if not open_tasks:
            await self._say(chat_id, tr(lang, "nothing_open"))
        elif len(open_tasks) == 1:
            await self._choose(user, chat_id, open_tasks[0])
        else:
            await self._say(
                chat_id,
                tr(lang, "which_task"),
                [*([self._proof_button(o, lang)] for o in open_tasks), cancel_row(lang)],
            )

    async def _ask_phone(self, chat_id: int, lang: str) -> None:
        await self._say(chat_id, tr(lang, "ask_phone"), menu=phone_menu_for(lang))

    async def _contact(self, user: User, chat_id: int, phone: str, own: bool) -> None:
        lang = user.locale.value
        if not own:
            await self._say(chat_id, tr(lang, "own_number_only"), menu=phone_menu_for(lang))
            return
        verified: str = await self._bus.handle(
            VerifyPhoneFromTelegram(chat_id=chat_id, phone=phone)
        )
        await self._say(chat_id, tr(lang, "phone_verified", phone=verified), menu=menu_for(lang))

    async def _settings(self, user: User, chat_id: int) -> None:
        lang = user.locale.value
        phone = (
            tr(lang, "phone_ok", phone=user.phone)
            if user.phone_verified
            else tr(lang, "phone_missing")
        )
        await self._say(
            chat_id,
            tr(lang, "settings_body", name=html(user.username), phone=phone),
            keyboard(
                []
                if user.phone_verified
                else [Button(tr(lang, "btn_verify_phone"), callback=Callback.PHONE)],
                site_row(self._web_url, "/profile", tr(lang, "btn_site")),
                [Button(tr(lang, "btn_help"), callback=Callback.HELP)],
                [Button(tr(lang, "btn_stop"), callback=Callback.STOP_ASK)],
            ),
        )

    async def _photo(self, user: User, chat_id: int, file_id: str, caption: str | None) -> None:
        lang = user.locale.value
        state = await self._conversation.get(chat_id)
        if "participation" in state:
            target = await self._open_task(user, UUID(hex=state["participation"]), state["task"])
            await self._submit(user, chat_id, target, file_id=file_id, text=caption)
            return
        candidates = [
            o for o in await self._open_tasks(user) if o.challenge.accepts(ProofType.PHOTO)
        ]
        if not candidates:
            await self._say(chat_id, tr(lang, "no_photo_tasks", today=label(lang, "today")))
        elif len(candidates) == 1:
            await self._submit(user, chat_id, candidates[0], file_id=file_id, text=caption)
        else:
            await self._conversation.update(chat_id, photo=file_id)
            await self._say(
                chat_id,
                tr(lang, "photo_which"),
                [*([self._proof_button(o, lang)] for o in candidates), cancel_row(lang)],
            )

    async def _text(self, user: User, chat_id: int, text: str) -> None:
        lang = user.locale.value
        state = await self._conversation.get(chat_id)
        if "participation" not in state:
            await self._say(chat_id, tr(lang, "press_proof", proof=label(lang, "proof")))
            return
        target = await self._open_task(user, UUID(hex=state["participation"]), state["task"])
        if not target.challenge.accepts(ProofType.TEXT):
            await self._say(chat_id, tr(lang, "needs_photo"))
            return
        await self._submit(user, chat_id, target, text=text[:2000])

    # --- use cases -------------------------------------------------------------------------

    async def _submit(
        self,
        user: User,
        chat_id: int,
        target: _Open,
        *,
        file_id: str | None = None,
        text: str | None = None,
    ) -> None:
        file_key = phash = None
        if file_id:
            data = await self._api.download(file_id)
            file_key, phash = await self._files.save(user.id, data)
        await self._bus.handle(
            SubmitProof(
                user_id=user.id,
                participation_id=target.participation.id,
                task_key=target.task.key,
                file_key=file_key,
                text_note=text or None,
                phash=phash,
            )
        )
        await self._conversation.clear(chat_id)
        lang = user.locale.value
        await self._say(chat_id, tr(lang, "accepted", title=html(self._task_name(target, lang))))

    async def _today(self, user: User, chat_id: int) -> None:
        lang = user.locale.value
        today = self._today_for(user)
        blocks: list[str] = []
        buttons: list[list[Button]] = []
        uow = self._uow()
        async with uow:
            for p, challenge in await self._participations(uow, user):
                proofs = await uow.proofs.list_for_day(p.id, today)
                block, open_tasks = self._board(p, challenge, proofs, today, lang)
                blocks.append(block)
                buttons.extend([self._proof_button(o, lang)] for o in open_tasks)
        if not blocks:
            await self._say(
                chat_id,
                tr(lang, "no_active"),
                keyboard(site_row(self._web_url, "/challenges", tr(lang, "btn_pick_challenge"))),
            )
            return
        footer = tr(lang, "pick_footer") if buttons else tr(lang, "all_done")
        header = tr(lang, "today_header", date=human_date(today, lang))
        await self._say(chat_id, "\n\n".join([header, *blocks, footer]), buttons)

    async def _status(self, user: User, chat_id: int) -> None:
        lang = user.locale.value
        lines = [tr(lang, "status_title")]
        uow = self._uow()
        async with uow:
            for p, challenge in await self._participations(uow, user):
                lines.append(
                    tr(
                        lang,
                        "status_block",
                        title=html(self._texts.title(challenge, lang)),
                        streak=p.current_streak,
                        best=p.best_streak,
                        done=p.days_completed,
                        total=len(p.days),
                        freezes=p.freezes_left,
                    )
                )
        if len(lines) == 1:
            lines.append(tr(lang, "no_active_status"))
        site = keyboard(site_row(self._web_url, "/profile", tr(lang, "btn_site")))
        await self._say(chat_id, "\n\n".join(lines), site)

    # --- helpers ---------------------------------------------------------------------------

    def _board(
        self,
        p: Participation,
        challenge: Challenge,
        proofs: list[Proof],
        today: date,
        lang: str = "uz",
    ) -> tuple[str, list[_Open]]:
        title = f"🎯 <b>{html(self._texts.title(challenge, lang))}</b>"
        if p.status is ParticipationStatus.SCHEDULED:
            return f"{title}\n{tr(lang, 'starts_on', date=human_date(p.start_date, lang))}", []
        lines = [f"{title} · 🔥 {p.current_streak}"]
        if today not in p.days:
            lines.append(tr(lang, "rest_day"))
            return "\n".join(lines), []
        roadmap = self._texts.roadmap(challenge, lang)
        focus = roadmap.focus(p.start_date, p.days, today) if roadmap else None
        if focus is not None:
            lines.append(
                tr(lang, "focus_line", week=focus.week, text=html(focus.lesson or focus.theme))
            )
        latest: dict[str, Proof] = {}
        for proof in sorted(proofs, key=lambda x: x.submitted_at):
            latest[proof.task_key] = proof
        open_tasks: list[_Open] = []
        for index, task in enumerate(p.tasks_on(today)):
            current = latest.get(task.key)
            icon, note_key = STATUS_ICON[current.status] if current else ("⬜", "")
            lines.append(
                tr(
                    lang,
                    "task_line",
                    icon=icon,
                    at=f"{task.at.strftime('%H:%M')} · " if task.at else "",
                    title=html(self._texts.task_title(challenge, task, lang)),
                    minutes=task.minutes,
                    optional="" if task.required else tr(lang, "optional"),
                    note=tr(lang, note_key) if note_key else "",
                )
            )
            if current is None or current.status is ProofStatus.REJECTED:
                with suppress(DomainError):
                    p.ensure_accepts_proof(today, task.key)
                    open_tasks.append(_Open(p, challenge, task, index))
        if p.is_stake and open_tasks:
            code = daily_code(self._code_secret, p.id, today)
            lines.append(tr(lang, "daily_code", code=code))
        return "\n".join(lines), open_tasks

    @staticmethod
    async def _participations(
        uow: TelegramUoW, user: User
    ) -> list[tuple[Participation, Challenge]]:
        result = []
        for participation_id in await uow.participations.list_open_ids(user.id):
            participation = await uow.participations.get(participation_id)
            if participation is None:
                continue
            challenge = await uow.challenges.get(participation.challenge_id)
            if challenge is not None:
                result.append((participation, challenge))
        return result

    async def _open_tasks(self, user: User) -> list[_Open]:
        today = self._today_for(user)
        result: list[_Open] = []
        uow = self._uow()
        async with uow:
            for p, challenge in await self._participations(uow, user):
                _, open_tasks = self._board(
                    p,
                    challenge,
                    await uow.proofs.list_for_day(p.id, today),
                    today,
                    user.locale.value,
                )
                result.extend(open_tasks)
        return result

    async def _open_task(self, user: User, participation_id: UUID, task_ref: str | int) -> _Open:
        """`task_ref` is a task key (saved conversation) or its index (button)."""
        uow = self._uow()
        async with uow:
            p = await uow.participations.get(participation_id)
            if p is None or p.user_id != user.id:
                raise DomainError(tr(user.locale.value, "not_found"))
            challenge = await uow.challenges.get(p.challenge_id)
        today = self._today_for(user)
        tasks = p.tasks_on(today)
        keys = [t.key for t in tasks]
        index = (
            task_ref
            if isinstance(task_ref, int)
            else keys.index(task_ref)
            if task_ref in keys
            else -1
        )
        if challenge is None or not 0 <= index < len(tasks):
            lang = user.locale.value
            raise DomainError(tr(lang, "not_in_plan", today=label(lang, "today")))
        p.ensure_accepts_proof(today, tasks[index].key)
        return _Open(p, challenge, tasks[index], index)

    def _ask_for_proof(self, user: User, target: _Open) -> str:
        photo = target.challenge.accepts(ProofType.PHOTO)
        text = target.challenge.accepts(ProofType.TEXT)
        lang = user.locale.value
        title = html(self._task_name(target, lang))
        key = "ask_photo_or_text" if photo and text else "ask_photo" if photo else "ask_text"
        ask = tr(lang, key, title=title)
        if photo and target.participation.is_stake:
            code = daily_code(self._code_secret, target.participation.id, self._today_for(user))
            ask += tr(lang, "code_in_photo", code=code)
        return ask

    def _task_name(self, target: _Open, lang: str) -> str:
        return self._texts.task_title(target.challenge, target.task, lang)

    def _proof_button(self, target: _Open, lang: str) -> Button:
        data = f"{PROOF_CALLBACK}:{target.participation.id.hex}:{target.index}"
        return Button(f"📸 {self._task_name(target, lang)[:40]}", callback=data)

    def _today_for(self, user: User) -> date:
        return local_date(self._clock.now(), user.timezone)

    async def _user(self, chat_id: int) -> User | None:
        uow = self._uow()
        async with uow:
            return await uow.users.get_by_telegram_chat(chat_id)

    async def _say(
        self, chat_id: int, text: str, buttons: Keyboard = (), *, menu: Menu | None = None
    ) -> None:
        try:
            await self._api.send(chat_id, text, buttons, menu=menu)
        except TelegramUnavailable:
            logger.warning("Could not answer Telegram chat %s", chat_id)
