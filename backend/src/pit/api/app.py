import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pit.api.routes import (
    admin,
    auth,
    challenges,
    media,
    plans,
    privacy,
    social,
    telegram,
    together,
    wallet,
)
from pit.config import get_settings
from pit.container import Container, build_container
from pit.jobs import DevScheduler
from pit.modules.telegram.infrastructure.runtime import TelegramPoller
from pit.modules.verification.infrastructure.storage import S3Storage
from pit.shared.application.errors import ConcurrencyConflict
from pit.shared.application.errors_i18n import translate_error
from pit.shared.domain.errors import DomainError, NotFound, PermissionDenied

logger = logging.getLogger(__name__)


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message})


def create_app(container: Container | None = None) -> FastAPI:
    settings = container.settings if container else get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = container is None
        active = container or build_container(settings)
        app.state.container = active
        if isinstance(active.storage, S3Storage):
            try:
                await active.storage.ensure_bucket()
            except Exception:
                logger.exception("Storage is not reachable; photo proofs will fail")
        scheduler = DevScheduler(active) if owned and settings.inline_tasks else None
        if scheduler:
            scheduler.start()
        poller = None
        if (
            owned
            and settings.telegram_mode == "polling"
            and active.telegram
            and active.telegram_api
        ):
            poller = TelegramPoller(active.telegram_api, active.telegram)
            poller.start()
        yield
        if poller:
            await poller.stop()
        if scheduler:
            await scheduler.stop()
        if owned:
            await active.close()

    app = FastAPI(
        title="Personal Improvement Together API",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def say(request: Request, message: str) -> str:
        """Errors are written in Uzbek; the client asks for its language in Accept-Language."""
        return translate_error(message, request.headers.get("accept-language"))

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status = (
            404 if isinstance(exc, NotFound) else 403 if isinstance(exc, PermissionDenied) else 422
        )
        return _error(status, exc.code, say(request, exc.message))

    @app.exception_handler(ConcurrencyConflict)
    async def conflict(request: Request, exc: ConcurrencyConflict) -> JSONResponse:
        message = "Ma'lumot shu payt o'zgardi, qayta urinib ko'ring"
        return _error(409, "conflict", say(request, message))

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return _error(exc.status_code, "http_error", say(request, str(exc.detail)))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:])
        message = f"Ma'lumot noto'g'ri: {field}".rstrip(": ")
        return _error(422, "validation_error", say(request, message))

    modules = (auth, challenges, plans, social, wallet, admin, media, telegram, together, privacy)
    for module in modules:
        app.include_router(module.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
