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
from pit.modules.verification.application.commands import SubmitProof
from pit.modules.verification.domain.daily_code import daily_code
from pit.modules.verification.domain.proof import Proof
from pit.modules.verification.domain.verdict import ProofStatus
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.messagebus import MessageBus
from pit.shared.domain.errors import DomainError

logger = logging.getLogger(__name__)

PROOF_CALLBACK = "p"  # p:<participation hex>:<task index> — fits Telegram's 64-byte limit


# The persistent menu under the input field — the bot is driven by these, not by commands.
class Label:
    TODAY = "📋 Bugungi vazifalar"
    PROOF = "📸 Isbot yuborish"
    STATUS = "📊 Natijalarim"
    SETTINGS = "⚙️ Sozlamalar"
    LATER = "⏭ Keyinroq"


MENU: Menu = [[Label.TODAY, Label.PROOF], [Label.STATUS, Label.SETTINGS]]
PHONE_MENU: Menu = [[ShareContact("📱 Raqamni yuborish")], [Label.LATER]]
PHONE_DEEP_LINK = "phone"  # t.me/<bot>?start=phone — from the website's phone card


class Callback:
    TODAY = TODAY_CALLBACK
    HELP = "help"
    CANCEL = "cancel"
    STOP_ASK = "stop?"
    STOP = "stop!"
    PHONE = "phone"


CANCEL_ROW = [Button("❌ Bekor qilish", callback=Callback.CANCEL)]

HELP = (
    "🤖 <b>Qanday ishlaydi</b>\n\n"
    f"{Label.TODAY} — bugun nima qilish kerak\n"
    f"{Label.PROOF} — vazifani tanlang va rasm yuboring\n"
    f"{Label.STATUS} — streak va progress\n"
    f"{Label.SETTINGS} — sayt va eslatmalar\n\n"
    "💡 Rasmni to'g'ridan-to'g'ri yuborsangiz ham bo'ladi — qaysi vazifa uchunligini "
    "o'zim so'rayman. Rasmga izoh yozsangiz, u ham isbotga qo'shiladi."
)
NOT_LINKED = (
    "👋 Assalomu alaykum! Men <b>PIT murabbiyi</b>man.\n\n"
    "Har kuni rejangizni eslatib turaman, isbotlaringizni qabul qilaman va har bir "
    "g'alabangizni nishonlayman 🔥\n\n"
    "Boshlash uchun saytda <b>Profil → Telegram'ni ulash</b> tugmasini bosing."
)
WELCOME = (
    "🎉 Salom, <b>{name}</b>! Telegram ulandi.\n\n"
    "Endi men sizga:\n"
    "☀️ ertalab — bugungi rejani,\n"
    "🌙 kechqurun — bajarilmagan vazifalarni,\n"
    "🏆 har bir yutuqda — tabrikni yuboraman.\n\n"
    "Hammasi pastdagi tugmalarda 👇"
)
STATUS_ICON = {
    ProofStatus.APPROVED: ("✅", ""),
    ProofStatus.PENDING: ("⏳", " · tekshirilmoqda"),
    ProofStatus.NEEDS_REVIEW: ("👀", " · moderator ko'rmoqda"),
    ProofStatus.REJECTED: ("❌", " · rad etildi, qayta yuboring"),
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
    ) -> None:
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
            await self._say(message.chat_id, f"⚠️ {html(error.message)}")
        finally:
            if message.callback_id:  # stops the spinner on the pressed button
                with suppress(TelegramUnavailable):
                    await self._api.answer_callback(message.callback_id)

    # --- routing ---------------------------------------------------------------------------

    async def _route(self, message: Incoming) -> None:
        chat_id = message.chat_id
        text = (message.text or "").strip()
        if text.startswith("/start"):
            await self._start(chat_id, text.removeprefix("/start").strip())
            return
        user = await self._user(chat_id)
        if user is None:
            await self._not_linked(chat_id)
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
        command = text.split()[0].split("@")[0].lower() if text.startswith("/") else text
        match command:
            case Label.TODAY | "/bugun" | "/today":
                await self._conversation.clear(chat_id)  # changed their mind: start over
                await self._today(user, chat_id)
            case Label.PROOF:
                await self._conversation.clear(chat_id)
                await self._pick_task(user, chat_id)
            case Label.STATUS | "/holat" | "/status":
                await self._status(user, chat_id)
            case Label.SETTINGS | "/stop":
                await self._settings(user, chat_id)
            case Label.LATER:
                await self._say(
                    chat_id, f"Mayli! Keyinroq «{Label.SETTINGS}» orqali tasdiqlaysiz 👌", menu=MENU
                )
            case _ if text.startswith("/"):
                await self._say(chat_id, HELP, menu=MENU)
            case _:
                return False
        return True

    async def _start(self, chat_id: int, token: str) -> None:
        if token == PHONE_DEEP_LINK:
            user = await self._user(chat_id)
            if user is None:
                await self._not_linked(chat_id)
            elif user.phone_verified:
                await self._say(chat_id, f"✅ Raqamingiz tasdiqlangan: {user.phone}", menu=MENU)
            else:
                await self._ask_phone(chat_id)
            return
        if token:
            user_id: UUID = await self._bus.handle(LinkTelegram(token=token, chat_id=chat_id))
            uow = self._uow()
            async with uow:
                user = await uow.users.get(user_id)
            name = user.username if user else ""
            await self._say(chat_id, WELCOME.format(name=html(name)), menu=MENU)
            if user is not None and not user.phone_verified:
                await self._ask_phone(chat_id)
            return
        if await self._user(chat_id) is not None:
            await self._say(chat_id, f"Siz allaqachon ulangansiz ✅\n\n{HELP}", menu=MENU)
        else:
            await self._not_linked(chat_id)

    async def _not_linked(self, chat_id: int) -> None:
        site = keyboard(site_row(self._web_url, "/profile"))
        # Without a site button there is room to hide a menu left from an earlier link.
        await self._say(chat_id, NOT_LINKED, site, menu=None if site else [])

    async def _callback(self, user: User, chat_id: int, data: str) -> None:
        match data:
            case Callback.TODAY:
                await self._today(user, chat_id)
                return
            case Callback.HELP:
                await self._say(chat_id, HELP, menu=MENU)
                return
            case Callback.PHONE:
                await self._ask_phone(chat_id)
                return
            case Callback.CANCEL:
                await self._conversation.clear(chat_id)
                await self._say(
                    chat_id, "👌 Bekor qilindi. Kerak bo'lsa, pastdagi menyudan tanlang."
                )
                return
            case Callback.STOP_ASK:
                await self._say(
                    chat_id,
                    "🔕 Eslatmalar va tabriklar kelmay qoladi. Rostdan o'chiramizmi?",
                    [
                        [
                            Button("✅ Ha, o'chirish", callback=Callback.STOP),
                            Button("↩️ Yo'q", callback=Callback.CANCEL),
                        ]
                    ],
                )
                return
            case Callback.STOP:
                await self._bus.handle(UnlinkTelegram(chat_id=chat_id))
                await self._conversation.clear(chat_id)
                await self._say(
                    chat_id,
                    "👋 Eslatmalar to'xtatildi. Qaytmoqchi bo'lsangiz — saytda "
                    "<b>Profil → Telegram'ni ulash</b>. Sizni kutib qolamiz!",
                    menu=[],
                )
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
        await self._say(chat_id, f"👏 {html(friend.username)} olqishingizni oldi!")

    async def _choose(self, user: User, chat_id: int, target: _Open) -> None:
        """Remember the task; the next photo or text the user sends proves it."""
        await self._conversation.update(
            chat_id, participation=target.participation.id.hex, task=target.task.key
        )
        await self._say(chat_id, self._ask_for_proof(user, target), [CANCEL_ROW])

    async def _pick_task(self, user: User, chat_id: int) -> None:
        open_tasks = await self._open_tasks(user)
        if not open_tasks:
            await self._say(chat_id, "🎉 Bugun isbot kutayotgan vazifa yo'q. Dam oling!")
        elif len(open_tasks) == 1:
            await self._choose(user, chat_id, open_tasks[0])
        else:
            await self._say(
                chat_id,
                "Qaysi vazifa uchun isbot yuborasiz? 👇",
                [*([self._proof_button(o)] for o in open_tasks), CANCEL_ROW],
            )

    async def _ask_phone(self, chat_id: int) -> None:
        await self._say(
            chat_id,
            "📱 <b>Telefon raqamingizni tasdiqlaymiz</b>\n\n"
            "Pastdagi tugmani bosing — Telegram raqamingizni o'zi yuboradi, hech narsa "
            "yozish shart emas. Raqam parolni tiklash va akkaunt xavfsizligi uchun kerak.",
            menu=PHONE_MENU,
        )

    async def _contact(self, user: User, chat_id: int, phone: str, own: bool) -> None:
        if not own:
            await self._say(chat_id, "Faqat o'zingizning raqamingizni yuboring 👇", menu=PHONE_MENU)
            return
        verified: str = await self._bus.handle(
            VerifyPhoneFromTelegram(chat_id=chat_id, phone=phone)
        )
        await self._say(chat_id, f"✅ Raqamingiz tasdiqlandi: <b>{verified}</b>", menu=MENU)

    async def _settings(self, user: User, chat_id: int) -> None:
        phone = (
            f"📱 Telefon: {user.phone} ✅" if user.phone_verified else "📱 Telefon: tasdiqlanmagan"
        )
        await self._say(
            chat_id,
            f"⚙️ <b>Sozlamalar</b>\n\n"
            f"👤 Akkaunt: <b>{html(user.username)}</b>\n"
            f"{phone}\n"
            "☀️ Ertalabki reja — 08:00\n"
            "🌙 Kechki eslatma — 20:00 (bajarilmagan vazifa qolsa)",
            keyboard(
                []
                if user.phone_verified
                else [Button("📱 Telefonni tasdiqlash", callback=Callback.PHONE)],
                site_row(self._web_url, "/profile", "🌐 Saytda ochish"),
                [Button("❓ Yordam", callback=Callback.HELP)],
                [Button("🔕 Eslatmalarni o'chirish", callback=Callback.STOP_ASK)],
            ),
        )

    async def _photo(self, user: User, chat_id: int, file_id: str, caption: str | None) -> None:
        state = await self._conversation.get(chat_id)
        if "participation" in state:
            target = await self._open_task(user, UUID(hex=state["participation"]), state["task"])
            await self._submit(user, chat_id, target, file_id=file_id, text=caption)
            return
        candidates = [
            o for o in await self._open_tasks(user) if o.challenge.accepts(ProofType.PHOTO)
        ]
        if not candidates:
            await self._say(chat_id, f"Bugun rasm kutayotgan vazifa yo'q 🙂 Ro'yxat: {Label.TODAY}")
        elif len(candidates) == 1:
            await self._submit(user, chat_id, candidates[0], file_id=file_id, text=caption)
        else:
            await self._conversation.update(chat_id, photo=file_id)
            await self._say(
                chat_id,
                "📸 Rasm keldi! Qaysi vazifa uchun?",
                [*([self._proof_button(o)] for o in candidates), CANCEL_ROW],
            )

    async def _text(self, user: User, chat_id: int, text: str) -> None:
        state = await self._conversation.get(chat_id)
        if "participation" not in state:
            await self._say(
                chat_id, f"Isbot yuborish uchun pastdagi «{Label.PROOF}» tugmasini bosing 👇"
            )
            return
        target = await self._open_task(user, UUID(hex=state["participation"]), state["task"])
        if not target.challenge.accepts(ProofType.TEXT):
            await self._say(chat_id, "Bu vazifa uchun rasm kerak 📸 Rasmni yuboring.")
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
        await self._say(
            chat_id,
            f"📨 <b>{html(target.task.title)}</b> — isbot qabul qilindi!\n"
            "Tekshirib, natijani shu yerga yozaman ⏳",
        )

    async def _today(self, user: User, chat_id: int) -> None:
        today = self._today_for(user)
        blocks: list[str] = []
        buttons: list[list[Button]] = []
        uow = self._uow()
        async with uow:
            for p, challenge in await self._participations(uow, user):
                proofs = await uow.proofs.list_for_day(p.id, today)
                block, open_tasks = self._board(p, challenge, proofs, today)
                blocks.append(block)
                buttons.extend([self._proof_button(o)] for o in open_tasks)
        if not blocks:
            await self._say(
                chat_id,
                "Hozir faol challenge yo'q. Yangisini boshlash vaqti keldi! 🚀",
                keyboard(site_row(self._web_url, "/challenges", "🚀 Challenge tanlash")),
            )
            return
        footer = (
            "Isbot yuborish uchun vazifani tanlang 👇"
            if buttons
            else "Bugungi hammasi joyida 🎉 Ertaga yana davom etamiz!"
        )
        header = f"📋 <b>Bugun</b> — {human_date(today)}"
        await self._say(chat_id, "\n\n".join([header, *blocks, footer]), buttons)

    async def _status(self, user: User, chat_id: int) -> None:
        lines = ["📊 <b>Natijalaringiz</b>"]
        uow = self._uow()
        async with uow:
            for p, challenge in await self._participations(uow, user):
                lines.append(
                    f"<b>{html(challenge.title)}</b>\n"
                    f"🔥 Streak: {p.current_streak} kun (rekord: {p.best_streak})\n"
                    f"📅 Bajarildi: {p.days_completed} / {len(p.days)} kun\n"
                    f"🧊 Freeze: {p.freezes_left} ta"
                )
        if len(lines) == 1:
            lines.append("Faol challenge yo'q. Saytda yangisini boshlang 🚀")
        await self._say(chat_id, "\n\n".join(lines), keyboard(site_row(self._web_url, "/profile")))

    # --- helpers ---------------------------------------------------------------------------

    def _board(
        self, p: Participation, challenge: Challenge, proofs: list[Proof], today: date
    ) -> tuple[str, list[_Open]]:
        title = f"🎯 <b>{html(challenge.title)}</b>"
        if p.status is ParticipationStatus.SCHEDULED:
            return f"{title}\n⏳ {human_date(p.start_date)} kuni boshlanadi", []
        lines = [f"{title} · 🔥 {p.current_streak}"]
        if today not in p.days:
            lines.append("😌 Bugun dam olish kuni — kuch yig'ing!")
            return "\n".join(lines), []
        latest: dict[str, Proof] = {}
        for proof in sorted(proofs, key=lambda x: x.submitted_at):
            latest[proof.task_key] = proof
        open_tasks: list[_Open] = []
        for index, task in enumerate(p.tasks_on(today)):
            current = latest.get(task.key)
            icon, note = STATUS_ICON[current.status] if current else ("⬜", "")
            optional = " · ixtiyoriy" if not task.required else ""
            lines.append(f"{icon} {html(task.title)} — {task.minutes} daq{optional}{note}")
            if current is None or current.status is ProofStatus.REJECTED:
                with suppress(DomainError):
                    p.ensure_accepts_proof(today, task.key)
                    open_tasks.append(_Open(p, challenge, task, index))
        if p.is_stake and open_tasks:
            code = daily_code(self._code_secret, p.id, today)
            lines.append(f"🔑 Kunlik kod: <code>{code}</code> (rasmda ko'rinsin)")
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
                    p, challenge, await uow.proofs.list_for_day(p.id, today), today
                )
                result.extend(open_tasks)
        return result

    async def _open_task(self, user: User, participation_id: UUID, task_ref: str | int) -> _Open:
        """`task_ref` is a task key (saved conversation) or its index (button)."""
        uow = self._uow()
        async with uow:
            p = await uow.participations.get(participation_id)
            if p is None or p.user_id != user.id:
                raise DomainError("Challenge topilmadi")
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
            raise DomainError(f"Bu vazifa bugungi rejada yo'q. Ro'yxat: {Label.TODAY}")
        p.ensure_accepts_proof(today, tasks[index].key)
        return _Open(p, challenge, tasks[index], index)

    def _ask_for_proof(self, user: User, target: _Open) -> str:
        photo = target.challenge.accepts(ProofType.PHOTO)
        text = target.challenge.accepts(ProofType.TEXT)
        title = html(target.task.title)
        if photo and text:
            ask = f"📸 <b>{title}</b> uchun rasm yuboring yoki nima qilganingizni yozing."
        elif photo:
            ask = f"📸 <b>{title}</b> uchun rasm yuboring."
        else:
            ask = f"✍️ <b>{title}</b> uchun nima qilganingizni yozib yuboring."
        if photo and target.participation.is_stake:
            code = daily_code(self._code_secret, target.participation.id, self._today_for(user))
            ask += f"\n🔑 Rasmda bugungi kod ko'rinsin: <code>{code}</code>"
        return ask

    @staticmethod
    def _proof_button(target: _Open) -> Button:
        data = f"{PROOF_CALLBACK}:{target.participation.id.hex}:{target.index}"
        return Button(f"📸 {target.task.title[:40]}", callback=data)

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
