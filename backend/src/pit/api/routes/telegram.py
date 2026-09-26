import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from pit.api import schemas as s
from pit.api.deps import ContainerDep, UserId
from pit.api.ratelimit import rate_limit
from pit.modules.identity.application.commands import IssueTelegramLink, UnlinkTelegram

router = APIRouter(tags=["telegram"])


@router.post("/telegram/webhook", include_in_schema=False)
async def webhook(
    request: Request,
    container: ContainerDep,
    secret: Annotated[str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")] = None,
) -> dict[str, bool]:
    """Telegram calls this with every message; the secret proves the call is really Telegram."""
    if container.telegram is None:
        raise HTTPException(404, "Telegram bot sozlanmagan")
    expected = container.settings.telegram_webhook_secret.get_secret_value()
    if not expected or not secret or not hmac.compare_digest(secret, expected):
        raise HTTPException(403, "Ruxsat yo'q")
    try:
        update = await request.json()
    except ValueError:
        return {"ok": True}
    if isinstance(update, dict):
        await container.telegram.process(update)
    return {"ok": True}  # always 200: otherwise Telegram redelivers the update


@router.post(
    "/me/telegram",
    response_model=s.TelegramLinkOut,
    dependencies=[Depends(rate_limit("telegram-link", 10, 3600, per="user"))],
)
async def link_telegram(user_id: UserId, container: ContainerDep) -> s.TelegramLinkOut:
    if container.telegram is None:
        raise HTTPException(404, "Telegram bot hozircha ulanmagan")
    token: str = await container.bus.handle(IssueTelegramLink(user_id=user_id))
    username = container.settings.telegram_bot_username
    return s.TelegramLinkOut(url=f"https://t.me/{username}?start={token}")


@router.delete("/me/telegram", status_code=204)
async def unlink_telegram(user_id: UserId, container: ContainerDep) -> None:
    await container.bus.handle(UnlinkTelegram(user_id=user_id))
