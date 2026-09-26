"""Pushes what the coach says to the user's Telegram chat.

Delivery is best effort: a Telegram outage is logged and never breaks the platform's own work;
a blocked bot unlinks the chat so nobody keeps writing to it."""

import logging

from pit.modules.coaching.domain.messages import Moment
from pit.modules.coaching.domain.notification import Notification, NotificationCreated
from pit.modules.identity.domain.user import User
from pit.modules.telegram.application.common import (
    CHEER_CALLBACK,
    TODAY_CALLBACK,
    TelegramUoW,
    html,
    keyboard,
    site_row,
)
from pit.modules.telegram.application.ports import (
    Button,
    ChatUnavailable,
    Keyboard,
    TelegramApi,
    TelegramUnavailable,
)
from pit.modules.verification.domain.events import ProofApproved
from pit.modules.verification.domain.verdict import ProofStatus

logger = logging.getLogger(__name__)

# Moments that invite the user to act today get a "send proof" button.
_ACT_NOW = {Moment.MORNING, Moment.EVENING_REMINDER, Moment.PROOF_REJECTED}
_FINAL = {Moment.CHALLENGE_COMPLETED, Moment.CHALLENGE_FAILED}


async def send_or_unlink(
    uow: TelegramUoW, user: User, text: str, buttons: Keyboard, telegram: TelegramApi
) -> None:
    """Call inside `async with uow`. Commits only when the chat turned out to be gone."""
    if user.telegram_chat_id is None:
        return
    try:
        await telegram.send(user.telegram_chat_id, text, buttons)
    except ChatUnavailable:
        logger.info("Telegram chat of %s is gone; unlinking", user.id)
        user.unlink_telegram()
        await uow.commit()
    except TelegramUnavailable:
        logger.warning("Telegram is unavailable; message to %s dropped", user.id)


def notification_keyboard(notification: Notification, web_url: str) -> Keyboard:
    action: list[Button] = []
    if notification.participation_id and notification.moment not in _FINAL:
        label = "📸 Isbot yuborish" if notification.moment in _ACT_NOW else "📋 Bugungi vazifalar"
        action = [Button(label, callback=TODAY_CALLBACK)]
    cheer: list[Button] = []
    if notification.moment is Moment.FRIEND_DAY_DONE and notification.subject_id:
        cheer = [Button("👏 Olqishlash", callback=f"{CHEER_CALLBACK}:{notification.id.hex}")]
    return keyboard(cheer, action, site_row(web_url, "/dashboard"))


async def deliver_notification(
    event: NotificationCreated, uow: TelegramUoW, *, telegram: TelegramApi, web_url: str
) -> None:
    async with uow:
        user = await uow.users.get(event.user_id)
        if user is None or user.telegram_chat_id is None:
            return
        notification = await uow.notifications.get(event.notification_id)
        if notification is None:
            return
        text = f"<b>{html(notification.title)}</b>\n\n{html(notification.body)}"
        await send_or_unlink(
            uow, user, text, notification_keyboard(notification, web_url), telegram
        )


class TelegramMessenger:
    """Identity's private channel (password reset codes) over the bot."""

    def __init__(self, telegram: TelegramApi) -> None:
        self._telegram = telegram

    async def send(self, user: User, text: str) -> bool:
        if user.telegram_chat_id is None:
            return False
        try:
            await self._telegram.send(user.telegram_chat_id, html(text))
        except (ChatUnavailable, TelegramUnavailable):
            return False
        return True


async def announce_task_approved(
    event: ProofApproved, uow: TelegramUoW, *, telegram: TelegramApi
) -> None:
    """A quick "✅ accepted" while other tasks remain. When this proof completes the day, the
    coach's day-done message follows instead, so we stay quiet to avoid a double message."""
    async with uow:
        user = await uow.users.get(event.user_id)
        if user is None or user.telegram_chat_id is None:
            return
        participation = await uow.participations.get(event.participation_id)
        if participation is None:
            return
        task = participation.task(event.day, event.task_key)
        if task is None:
            return
        approved = {
            proof.task_key
            for proof in await uow.proofs.list_for_day(participation.id, event.day)
            if proof.status is ProofStatus.APPROVED
        } | {event.task_key}
        remaining = [
            t for t in participation.tasks_on(event.day) if t.required and t.key not in approved
        ]
        if task.required and not remaining:
            return
        text = f"✅ <b>{html(task.title)}</b> tasdiqlandi!"
        buttons: Keyboard = ()
        if remaining:
            text += f"\nYana {len(remaining)} ta majburiy vazifa qoldi — davom eting 💪"
            buttons = [[Button("📋 Bugungi vazifalar", callback=TODAY_CALLBACK)]]
        elif not task.required:
            text += "\nQo'shimcha ball qo'shildi ⭐"
        await send_or_unlink(uow, user, text, buttons, telegram)
