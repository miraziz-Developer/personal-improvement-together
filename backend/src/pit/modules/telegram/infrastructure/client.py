"""Telegram Bot API over httpx, and parsing of incoming updates."""

import asyncio
import logging
from typing import Any

import httpx

from pit.modules.telegram.application.ports import (
    Button,
    ChatUnavailable,
    Incoming,
    Keyboard,
    Menu,
    OpenApp,
    ShareContact,
    TelegramUnavailable,
)
from pit.modules.verification.infrastructure.images import MAX_UPLOAD_BYTES
from pit.shared.domain.errors import DomainError

logger = logging.getLogger(__name__)
# httpx logs every request URL at INFO, and Bot API URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

API = "https://api.telegram.org"
# The bot is driven by buttons; /start only brings the menu back if it was hidden.
COMMANDS = [{"command": "start", "description": "🏠 Menyuni ochish"}]
ALLOWED_UPDATES = ["message", "callback_query"]
# Shown on the bot's empty chat screen and in its profile.
DESCRIPTION = (
    "🔥 PIT murabbiyi — maqsadlaringizni har kungi odatga aylantiraman.\n\n"
    "☀️ Ertalab bugungi rejani eslataman\n"
    "📸 Isbotni shu yerda qabul qilaman\n"
    "🏆 Har bir g'alabangizni nishonlayman\n\n"
    "Boshlash: pastdagi «PIT» tugmasini bosing — ilova shu yerda, Telegram ichida ochiladi."
)
SHORT_DESCRIPTION = "Har kungi reja, eslatma va isbot — PIT murabbiyi 🔥"


def _button(button: Button) -> dict[str, Any]:
    if button.app:
        return {"text": button.text, "web_app": {"url": button.app}}
    if button.url:
        return {"text": button.text, "url": button.url}
    return {"text": button.text, "callback_data": button.callback or ""}


def _menu_button(button: str | ShareContact | OpenApp) -> dict[str, Any]:
    if isinstance(button, OpenApp):
        return {"text": button.text, "web_app": {"url": button.url}}
    if isinstance(button, ShareContact):
        return {"text": button.text, "request_contact": True}
    return {"text": button}


class HttpTelegramApi:
    def __init__(self, token: str, client: httpx.AsyncClient) -> None:
        self._base = f"{API}/bot{token}"
        self._files = f"{API}/file/bot{token}"
        self._client = client

    async def call(
        self, method: str, payload: dict[str, Any] | None = None, *, timeout: float = 10
    ) -> Any:
        for attempt in (1, 2):
            try:
                response = await self._client.post(
                    f"{self._base}/{method}", json=payload or {}, timeout=timeout
                )
                data = response.json()
            except (httpx.HTTPError, ValueError) as error:
                # Never put the exception text in the message: it may contain the token URL.
                raise TelegramUnavailable(f"{method}: {type(error).__name__}") from None
            if data.get("ok"):
                return data.get("result")
            description = str(data.get("description", ""))
            if response.status_code == 403 or "chat not found" in description.lower():
                raise ChatUnavailable(description)
            retry_after = int((data.get("parameters") or {}).get("retry_after", 0))
            if response.status_code == 429 and attempt == 1 and retry_after <= 5:
                await asyncio.sleep(retry_after)
                continue
            raise TelegramUnavailable(f"{method}: {response.status_code} {description}")
        raise AssertionError("unreachable")

    async def send(
        self, chat_id: int, text: str, keyboard: Keyboard = (), *, menu: Menu | None = None
    ) -> None:
        if keyboard and menu is not None:
            raise ValueError("A message carries either inline buttons or the menu")
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if keyboard:
            payload["reply_markup"] = {
                "inline_keyboard": [[_button(b) for b in row] for row in keyboard]
            }
        elif menu:
            payload["reply_markup"] = {
                "keyboard": [[_menu_button(b) for b in row] for row in menu],
                "resize_keyboard": True,
                "is_persistent": True,
                "input_field_placeholder": "Menyudan tanlang yoki rasm yuboring",
            }
        elif menu is not None:
            payload["reply_markup"] = {"remove_keyboard": True}
        await self.call("sendMessage", payload)

    async def answer_callback(self, callback_id: str, text: str = "") -> None:
        await self.call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})

    async def download(self, file_id: str) -> bytes:
        info = await self.call("getFile", {"file_id": file_id})
        if int(info.get("file_size") or 0) > MAX_UPLOAD_BYTES:
            raise DomainError("Rasm 10 MB dan oshmasligi kerak")
        try:
            response = await self._client.get(f"{self._files}/{info['file_path']}", timeout=30)
            response.raise_for_status()
        except httpx.HTTPError:
            raise TelegramUnavailable("download failed") from None
        return response.content

    async def configure(
        self, *, webhook_url: str | None, secret: str, app_url: str | None = None
    ) -> None:
        """Webhook (production) or none (local polling), the command menu and the menu button
        that opens the site inside Telegram (`app_url`, https only)."""
        if webhook_url:
            await self.call(
                "setWebhook",
                {"url": webhook_url, "secret_token": secret, "allowed_updates": ALLOWED_UPDATES},
            )
        else:
            await self.call("deleteWebhook")
        await self.call("setMyCommands", {"commands": COMMANDS})
        await self.call("setMyDescription", {"description": DESCRIPTION})
        await self.call("setMyShortDescription", {"short_description": SHORT_DESCRIPTION})
        if app_url:
            button = {"type": "web_app", "text": "PIT", "web_app": {"url": app_url}}
            await self.call("setChatMenuButton", {"menu_button": button})

    async def updates(self, offset: int) -> list[dict[str, Any]]:
        """Long polling for local development (no public URL for a webhook)."""
        payload = {"offset": offset, "timeout": 25, "allowed_updates": ALLOWED_UPDATES}
        result: list[dict[str, Any]] = await self.call("getUpdates", payload, timeout=35)
        return result


def parse_update(update: dict[str, Any]) -> Incoming | None:
    """Private chats only; everything else (groups, edits, channel posts) is ignored."""
    if query := update.get("callback_query"):
        chat = (query.get("message") or {}).get("chat") or {}
        if chat.get("type") != "private":
            return None
        return Incoming(
            chat_id=int(chat["id"]),
            callback_id=str(query["id"]),
            callback_data=str(query.get("data") or ""),
            language=(query.get("from") or {}).get("language_code"),
        )
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    if chat.get("type") != "private":
        return None
    photo_file_id = None
    if photos := message.get("photo"):
        photo_file_id = str(photos[-1]["file_id"])  # sizes come smallest first
    elif (document := message.get("document")) and str(document.get("mime_type", "")).startswith(
        "image/"
    ):
        photo_file_id = str(document["file_id"])
    contact = message.get("contact") or {}
    sender = (message.get("from") or {}).get("id")
    return Incoming(
        chat_id=int(chat["id"]),
        text=message.get("text"),
        photo_file_id=photo_file_id,
        caption=message.get("caption"),
        contact_phone=contact.get("phone_number"),
        contact_is_own=sender is not None and contact.get("user_id") == sender,
        language=(message.get("from") or {}).get("language_code"),
        sender=(message.get("from") or {}).get("username")
        or (message.get("from") or {}).get("first_name"),
    )
