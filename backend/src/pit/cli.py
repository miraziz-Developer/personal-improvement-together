"""Admin commands:

uv run python -m pit.cli seed                     # add the ready-made challenges
uv run python -m pit.cli make-moderator <username>
uv run python -m pit.cli close-days               # run the daily job once
uv run python -m pit.cli nudges morning|evening   # send the coach's messages now
uv run python -m pit.cli telegram-setup           # register the bot webhook and command menu
uv run python -m pit.cli ai-check                 # prove the configured AI really answers
uv run python -m pit.cli weekly                   # send the Sunday summaries now
uv run python -m pit.cli vapid-keys               # key pair for browser push notifications
"""

import argparse
import asyncio
import base64
import io
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from PIL import Image, ImageDraw
from py_vapid import Vapid

from pit.catalog import build_catalog
from pit.config import Settings, get_settings
from pit.container import Container, ai_pool, build_container
from pit.jobs import close_all_days, send_nudges, send_weekly_summaries
from pit.modules.challenges.domain.challenge import Category
from pit.modules.planning.domain.plan import Availability, OnboardingAnswers
from pit.modules.planning.infrastructure.generators import (
    LlmPlanGenerator,
    TemplatePlanGenerator,
)
from pit.modules.verification.application.ports import VerificationRequest
from pit.modules.verification.infrastructure.ai import LlmProofVerifier
from pit.modules.verification.infrastructure.storage import InMemoryStorage
from pit.shared.infrastructure.llm import AiUnavailable, LlmPool


async def seed(container: Container) -> int:
    added = 0
    async with container.uow_factory() as uow:
        for challenge in build_catalog():
            if await uow.challenges.get(challenge.id) is None:
                uow.challenges.add(challenge)
                added += 1
        await uow.commit()
    return added


async def make_moderator(container: Container, username: str) -> None:
    async with container.uow_factory() as uow:
        user = await uow.users.get_by_username(username.strip().lower())
        if user is None:
            raise SystemExit(f"User '{username}' not found")
        user.promote_to_moderator()
        await uow.commit()


async def telegram_setup(container: Container) -> str:
    settings = container.settings
    if container.telegram_api is None:
        return "Telegram bot is not configured (PIT_TELEGRAM_BOT_TOKEN is empty) — skipped"
    if settings.telegram_mode == "polling":
        await container.telegram_api.configure(webhook_url=None, secret="")
        return "Polling mode: the API process pulls updates itself"
    secret = settings.telegram_webhook_secret.get_secret_value()
    if not secret:
        raise SystemExit("Set PIT_TELEGRAM_WEBHOOK_SECRET before registering the webhook")
    url = f"{settings.public_base_url.rstrip('/')}/api/v1/telegram/webhook"
    await container.telegram_api.configure(webhook_url=url, secret=secret)
    return f"Webhook registered: {url}"


async def ai_check(settings: Settings) -> None:
    """The live platform hides AI outages behind fallbacks, so check every provider here."""
    pool, plan_pool = ai_pool(settings, "proof"), ai_pool(settings, "plan")
    if pool is None or plan_pool is None:
        raise SystemExit("AI is off: set PIT_AI_PROVIDERS and the providers' API keys")
    image = Image.new("RGB", (320, 240), (40, 120, 60))
    ImageDraw.Draw(image).text((20, 100), "Bugun 5 km yugurdim", fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG")
    storage = InMemoryStorage()
    await storage.put("check.jpg", buffer.getvalue(), "image/jpeg")
    request = VerificationRequest(
        proof_id=uuid4(),
        category=Category.SPORT,
        criteria="Rasmda yugurish yoki sport faoliyati ko'rinsin",
        file_key="check.jpg",
        text_note="Bugun 5 km yugurdim",
        expected_code=None,
    )
    answers = OnboardingAnswers(
        goal="Har kuni kitob o'qishni odat qilish",
        motivation="Ko'proq bilim",
        current_level="Oyiga 1 ta kitob",
        obstacles="Telefon",
        availability=Availability.from_mapping(dict.fromkeys(range(7), 60)),
    )
    for endpoint in pool.endpoints:
        try:
            verdict = await LlmProofVerifier(LlmPool([endpoint]), storage).verify(request)
            print(f"✅ {endpoint.label} proof: {verdict.decision} — {verdict.reason}")
        except AiUnavailable as error:
            print(f"❌ {endpoint.label} proof: {type(error.__cause__).__name__}")
    for endpoint in plan_pool.endpoints:
        try:
            plan = await LlmPlanGenerator(LlmPool([endpoint]), TemplatePlanGenerator()).ask(answers)
            print(f"✅ {endpoint.label} plan: {plan.title} ({plan.duration_days} kun)")
        except AiUnavailable as error:
            print(f"❌ {endpoint.label} plan: {type(error.__cause__).__name__}")


def vapid_keys() -> str:
    """A fresh key pair for browser push notifications, ready to paste into .env."""
    vapid = Vapid()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    return (
        f"PIT_VAPID_PUBLIC_KEY={base64.urlsafe_b64encode(public).decode().rstrip('=')}\n"
        f"PIT_VAPID_PRIVATE_KEY={base64.urlsafe_b64encode(private).decode().rstrip('=')}"
    )


async def main() -> None:
    parser = argparse.ArgumentParser(prog="pit")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    moderator = sub.add_parser("make-moderator")
    moderator.add_argument("username")
    sub.add_parser("close-days")
    nudges = sub.add_parser("nudges")
    nudges.add_argument("kind", choices=["morning", "evening"])
    sub.add_parser("telegram-setup")
    sub.add_parser("ai-check")
    sub.add_parser("weekly")
    sub.add_parser("vapid-keys")
    args = parser.parse_args()

    if args.command == "vapid-keys":
        print(vapid_keys())
        return
    if args.command == "ai-check":
        await ai_check(get_settings())
        return
    container = build_container(get_settings())
    try:
        match args.command:
            case "seed":
                print(f"Added {await seed(container)} challenges")
            case "make-moderator":
                await make_moderator(container, args.username)
                print(f"{args.username} is now a moderator")
            case "close-days":
                print(f"Closed days for {await close_all_days(container)} participations")
            case "nudges":
                print(f"Sent {await send_nudges(container, args.kind)} messages")
            case "weekly":
                print(f"Sent {await send_weekly_summaries(container)} weekly summaries")
            case "telegram-setup":
                print(await telegram_setup(container))
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
