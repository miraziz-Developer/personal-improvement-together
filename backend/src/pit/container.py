"""Builds the real application: settings -> adapters -> message bus. Tests pass overrides."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import httpx
from openai import AsyncAzureOpenAI, AsyncOpenAI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine

from pit.bootstrap import Dependencies, bootstrap
from pit.config import Settings
from pit.infrastructure.unit_of_work import SqlAlchemyUnitOfWork
from pit.modules.identity.application.ports import GoogleVerifier, OtpStore, SmsSender
from pit.modules.identity.infrastructure.google import GoogleIdTokenVerifier
from pit.modules.identity.infrastructure.security import (
    Argon2PasswordHasher,
    ConsoleSmsSender,
    EskizSmsSender,
    RedisLinkTokens,
    RedisOtpStore,
)
from pit.modules.planning.application.ports import PlanGenerator
from pit.modules.planning.infrastructure.generators import (
    LlmPlanGenerator,
    TemplatePlanGenerator,
)
from pit.modules.ranking.infrastructure.leaderboard import RedisLeaderboard
from pit.modules.telegram.application.bot import TelegramBot
from pit.modules.telegram.application.ports import TelegramApi
from pit.modules.telegram.infrastructure.client import HttpTelegramApi
from pit.modules.telegram.infrastructure.runtime import (
    RedisConversation,
    StoredProofFiles,
    TelegramGateway,
)
from pit.modules.verification.application.commands import VerifyProof
from pit.modules.verification.application.ports import ProofVerifier
from pit.modules.verification.infrastructure.ai import (
    DevProofVerifier,
    LlmProofVerifier,
    ResilientVerifier,
)
from pit.modules.verification.infrastructure.storage import (
    FileStorage,
    InMemoryStorage,
    LocalFileStorage,
    S3Storage,
)
from pit.shared.application.clock import Clock, SystemClock
from pit.shared.application.messagebus import MessageBus
from pit.shared.infrastructure.db import create_engine, create_session_factory
from pit.shared.infrastructure.llm import LlmEndpoint, LlmPool

logger = logging.getLogger(__name__)


class InlineVerificationQueue:
    """Local development: verify right after the proof is committed, inside the API process."""

    def __init__(self) -> None:
        self.bus: MessageBus | None = None
        self._running: set[asyncio.Task[Any]] = set()

    async def enqueue(self, proof_id: UUID) -> None:
        if self.bus is None:
            raise RuntimeError("InlineVerificationQueue is not wired to a bus")
        task = asyncio.create_task(self.bus.handle(VerifyProof(proof_id=proof_id)))
        self._running.add(task)
        task.add_done_callback(self._running.discard)

    async def drain(self) -> None:
        while self._running:
            await asyncio.gather(*self._running, return_exceptions=True)


class CeleryVerificationQueue:
    def __init__(self, settings: Settings) -> None:
        from pit.celery_app import make_celery

        self._app = make_celery(settings)

    async def enqueue(self, proof_id: UUID) -> None:
        await asyncio.to_thread(self._app.send_task, "pit.verify_proof", args=[str(proof_id)])


@dataclass
class Container:
    settings: Settings
    engine: AsyncEngine
    uow_factory: Callable[[], SqlAlchemyUnitOfWork]
    bus: MessageBus
    redis: Any
    storage: FileStorage
    leaderboard: RedisLeaderboard
    hasher: Argon2PasswordHasher
    clock: Clock
    queue: InlineVerificationQueue | CeleryVerificationQueue
    http: httpx.AsyncClient
    telegram: TelegramGateway | None = None  # None = no bot configured
    telegram_api: HttpTelegramApi | None = None

    async def close(self) -> None:
        if isinstance(self.queue, InlineVerificationQueue):
            await self.queue.drain()
        await self.engine.dispose()
        await self.redis.aclose()
        await self.http.aclose()


AI_TIMEOUT_SECONDS = 60.0
AI_BASE_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq": "https://api.groq.com/openai/v1",
}


type AiPurpose = Literal["proof", "plan"]


def _ai_endpoint(
    settings: Settings, name: str, retries: int, purpose: AiPurpose = "proof"
) -> LlmEndpoint | None:
    """One configured provider, or None when its key is missing."""
    options: dict[str, Any] = {"max_retries": retries, "timeout": AI_TIMEOUT_SECONDS}
    match name:
        case "gemini" | "groq":
            key = getattr(settings, f"{name}_api_key").get_secret_value()
            model = _model(settings, name, purpose)
            client: Any = AsyncOpenAI(api_key=key, base_url=AI_BASE_URLS[name], **options)
        case "openai":
            key, model = settings.openai_api_key.get_secret_value(), _model(settings, name, purpose)
            client = AsyncOpenAI(api_key=key, base_url=settings.openai_base_url, **options)
        case _:
            key, model = settings.azure_api_key.get_secret_value(), settings.azure_deployment
            client = AsyncAzureOpenAI(
                api_key=key,
                azure_endpoint=settings.azure_endpoint or "",
                api_version=settings.azure_api_version,
                **options,
            )
    return LlmEndpoint(name=name, client=client, model=model) if key else None


def _model(settings: Settings, name: str, purpose: AiPurpose) -> str:
    vision: str = getattr(settings, f"{name}_model")
    return (getattr(settings, f"{name}_plan_model") or vision) if purpose == "plan" else vision


def ai_pool(settings: Settings, purpose: AiPurpose = "proof") -> LlmPool | None:
    names = settings.ai_provider_names
    # With company, fail over fast; alone, a provider gets a few patient retries.
    retries = 1 if len(names) > 1 else 4
    endpoints = []
    for name in names:
        endpoint = _ai_endpoint(settings, name, retries, purpose)
        if endpoint is None:
            logger.warning("AI provider %s has no API key; skipped", name)
        else:
            endpoints.append(endpoint)
    if not endpoints and not settings.is_local and purpose == "proof":
        logger.error("No AI provider configured: every proof will be approved without a check")
    return LlmPool(endpoints) if endpoints else None


def _storage(settings: Settings) -> FileStorage:
    match settings.storage:
        case "s3":
            return S3Storage(
                endpoint_url=settings.s3_endpoint_url,
                bucket=settings.s3_bucket,
                access_key=settings.s3_access_key,
                secret_key=settings.s3_secret_key.get_secret_value(),
            )
        case "local":
            return LocalFileStorage(
                root=Path(settings.local_storage_dir),
                public_base_url=settings.public_base_url,
                secret=settings.jwt_secret.get_secret_value().encode(),
            )
        case _:
            return InMemoryStorage()


def build_container(
    settings: Settings,
    *,
    redis: Any | None = None,
    storage: FileStorage | None = None,
    verifier: ProofVerifier | None = None,
    plan_generator: PlanGenerator | None = None,
    otp_store: OtpStore | None = None,
    sms_sender: SmsSender | None = None,
    clock: Clock | None = None,
    telegram_api: TelegramApi | None = None,
    google: GoogleVerifier | None = None,
) -> Container:
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    def uow_factory() -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory)

    redis = (
        redis if redis is not None else Redis.from_url(settings.redis_url, decode_responses=True)
    )
    if storage is None:
        storage = _storage(settings)
    if verifier is None:
        proof_ai = ai_pool(settings, "proof")
        verifier = (
            ResilientVerifier(LlmProofVerifier(proof_ai, storage))
            if proof_ai
            else DevProofVerifier()
        )
    if plan_generator is None:
        plan_ai, template = ai_pool(settings, "plan"), TemplatePlanGenerator()
        plan_generator = LlmPlanGenerator(plan_ai, template) if plan_ai else template
    queue: InlineVerificationQueue | CeleryVerificationQueue = (
        InlineVerificationQueue() if settings.inline_tasks else CeleryVerificationQueue(settings)
    )
    clock = clock or SystemClock()
    hasher = Argon2PasswordHasher()
    http = httpx.AsyncClient(timeout=10)
    if sms_sender is None:
        sms_sender = (
            EskizSmsSender(
                email=settings.eskiz_email,
                password=settings.eskiz_password.get_secret_value(),
                sender=settings.eskiz_sender,
                client=http,
            )
            if settings.sms_provider == "eskiz"
            else ConsoleSmsSender()
        )
    leaderboard = RedisLeaderboard(redis)
    http_telegram: HttpTelegramApi | None = None
    if telegram_api is None and settings.telegram_enabled:
        http_telegram = HttpTelegramApi(settings.telegram_bot_token.get_secret_value(), http)
        telegram_api = http_telegram
    code_secret = settings.daily_code_secret.get_secret_value().encode()
    if google is None and settings.google_client_id:
        google = GoogleIdTokenVerifier(settings.google_client_id)
    bus = bootstrap(
        Dependencies(
            uow_factory=uow_factory,
            clock=clock,
            verifier=verifier,
            verification_queue=queue,
            leaderboard=leaderboard,
            plan_generator=plan_generator,
            password_hasher=hasher,
            otp_store=otp_store or RedisOtpStore(redis),
            sms_sender=sms_sender,
            link_tokens=RedisLinkTokens(redis),
            daily_code_secret=code_secret,
            stakes_enabled=settings.stakes_enabled,
            telegram=telegram_api,
            web_url=settings.web_url,
            google=google,
        )
    )
    gateway = None
    if telegram_api is not None:
        bot = TelegramBot(
            bus=bus,
            uow_factory=uow_factory,
            api=telegram_api,
            conversation=RedisConversation(redis),
            files=StoredProofFiles(storage),
            clock=clock,
            code_secret=code_secret,
            web_url=settings.web_url,
        )
        gateway = TelegramGateway(
            bot, telegram_api, redis, rate_limits=settings.rate_limits_enabled
        )
    if isinstance(queue, InlineVerificationQueue):
        queue.bus = bus
    return Container(
        settings=settings,
        engine=engine,
        uow_factory=uow_factory,
        bus=bus,
        redis=redis,
        storage=storage,
        leaderboard=leaderboard,
        hasher=hasher,
        clock=clock,
        queue=queue,
        http=http,
        telegram=gateway,
        telegram_api=http_telegram,
    )
