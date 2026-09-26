import re
import secrets
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from pit.api import schemas as s
from pit.api.deps import ContainerDep, UserId
from pit.api.ratelimit import client_ip, enforce, rate_limit
from pit.api.security import issue_signup_token, issue_token, read_signup_token
from pit.modules.coaching.domain.messages import quote_of_the_day
from pit.modules.identity.application.commands import (
    ConfirmPhone,
    RegisterUser,
    RegisterWithGoogle,
    RequestPasswordReset,
    RequestPhoneCode,
    ResetPassword,
    SignInWithGoogle,
)
from pit.modules.identity.application.handlers import authenticate
from pit.modules.identity.application.ports import GoogleIdentity
from pit.modules.identity.domain.user import CURRENT_TERMS_VERSION
from pit.modules.identity.infrastructure.tables import regions
from pit.shared.application.clock import local_date

router = APIRouter(tags=["auth"])


@router.post(
    "/auth/register",
    response_model=s.TokenOut,
    status_code=201,
    dependencies=[Depends(rate_limit("register", 5, 3600))],
)
async def register(body: s.RegisterIn, container: ContainerDep) -> s.TokenOut:
    user_id = await container.bus.handle(
        RegisterUser(
            username=body.username,
            password=body.password,
            birth_date=body.birth_date,
            region_id=body.region_id,
            accepted_terms_version=body.accepted_terms_version,
        )
    )
    token = issue_token(user_id, container.settings, container.clock.now())
    return s.TokenOut(access_token=token, user_id=user_id)


@router.post("/auth/login", response_model=s.TokenOut)
async def login(body: s.LoginIn, request: Request, container: ContainerDep) -> s.TokenOut:
    # Per IP and per account: stops both one attacker trying many accounts and many
    # machines trying one account.
    await enforce(container, f"login-ip:{client_ip(request, container)}", 20, 900)
    await enforce(container, f"login-user:{body.username.strip().lower()}", 10, 900)
    user = await authenticate(
        container.uow_factory(), container.hasher, body.username, body.password
    )
    token = issue_token(user.id, container.settings, container.clock.now())
    return s.TokenOut(access_token=token, user_id=user.id)


async def _suggest_username(container: ContainerDep, email: str | None) -> str:
    base = re.sub(r"[^a-z0-9_]", "_", (email or "").split("@")[0].lower()).strip("_")[:24]
    base = base if len(base) >= 3 else "user"
    async with container.uow_factory() as uow:
        candidate = base
        while await uow.users.get_by_username(candidate):
            candidate = f"{base}_{secrets.randbelow(1000)}"
    return candidate


@router.post(
    "/auth/google",
    response_model=s.GoogleOut,
    dependencies=[Depends(rate_limit("google", 30, 900))],
)
async def google_sign_in(body: s.GoogleIn, container: ContainerDep) -> s.GoogleOut:
    """Known Google account → signed in. New one → a short-lived token to finish the profile
    (birth date and region are required and Google does not provide them)."""
    if not container.settings.google_client_id:
        raise HTTPException(404, "Google orqali kirish yoqilmagan")
    now = container.clock.now()
    result = await container.bus.handle(SignInWithGoogle(credential=body.credential))
    if isinstance(result, GoogleIdentity):
        return s.GoogleOut(
            signup_token=issue_signup_token(result.sub, result.email, container.settings, now),
            email=result.email,
            suggested_username=await _suggest_username(container, result.email),
        )
    return s.GoogleOut(access_token=issue_token(result, container.settings, now), user_id=result)


@router.post(
    "/auth/google/register",
    response_model=s.TokenOut,
    status_code=201,
    dependencies=[Depends(rate_limit("register", 5, 3600))],
)
async def google_register(body: s.GoogleRegisterIn, container: ContainerDep) -> s.TokenOut:
    try:
        google_sub, email = read_signup_token(body.signup_token, container.settings)
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(422, "Vaqt tugadi. Google orqali qaytadan kiring") from None
    user_id = await container.bus.handle(
        RegisterWithGoogle(
            google_sub=google_sub,
            email=email,
            username=body.username,
            birth_date=body.birth_date,
            region_id=body.region_id,
            accepted_terms_version=body.accepted_terms_version,
        )
    )
    token = issue_token(user_id, container.settings, container.clock.now())
    return s.TokenOut(access_token=token, user_id=user_id)


@router.post(
    "/auth/password/forgot",
    status_code=204,
    dependencies=[Depends(rate_limit("forgot", 5, 3600))],
)
async def forgot_password(body: s.ForgotIn, container: ContainerDep) -> None:
    await container.bus.handle(RequestPasswordReset(username=body.username))


@router.post(
    "/auth/password/reset",
    status_code=204,
    dependencies=[Depends(rate_limit("reset", 10, 3600))],
)
async def reset_password(body: s.ResetIn, container: ContainerDep) -> None:
    await container.bus.handle(
        ResetPassword(username=body.username, code=body.code, new_password=body.new_password)
    )


@router.post(
    "/auth/phone/request",
    status_code=204,
    dependencies=[Depends(rate_limit("phone-request", 3, 600, per="user"))],
)
async def request_phone_code(
    body: s.PhoneRequestIn, user_id: UserId, container: ContainerDep
) -> None:
    await container.bus.handle(RequestPhoneCode(user_id=user_id, phone=body.phone))


@router.post(
    "/auth/phone/confirm",
    status_code=204,
    dependencies=[Depends(rate_limit("phone-confirm", 10, 600, per="user"))],
)
async def confirm_phone(body: s.PhoneConfirmIn, user_id: UserId, container: ContainerDep) -> None:
    await container.bus.handle(ConfirmPhone(user_id=user_id, code=body.code))


@router.get("/features", tags=["meta"])
async def features(container: ContainerDep) -> dict[str, bool | str | None]:
    """Lets the frontend hide switched-off features (e.g. paid stake mode)."""
    return {
        "stakes_enabled": container.settings.stakes_enabled,
        "terms_version": CURRENT_TERMS_VERSION,
        "telegram_bot": (
            container.settings.telegram_bot_username if container.telegram is not None else None
        ),
        # Public by design: Google's button needs it in the browser.
        "google_client_id": container.settings.google_client_id or None,
        "sms_enabled": container.settings.sms_provider == "eskiz",
        "push_public_key": container.settings.vapid_public_key or None,
    }


@router.get("/regions", response_model=list[s.RegionOut], tags=["meta"])
async def list_regions(container: ContainerDep) -> list[s.RegionOut]:
    async with container.uow_factory() as uow:
        rows = await uow.session.execute(select(regions).order_by(regions.c.name_uz))
        return [s.RegionOut(**row) for row in rows.mappings()]


@router.get("/quote", response_model=s.QuoteOut, tags=["meta"])
async def quote(
    container: ContainerDep, lang: Annotated[str, Query(max_length=5)] = "uz"
) -> s.QuoteOut:
    text, author = quote_of_the_day(local_date(container.clock.now(), "Asia/Tashkent"), lang)
    return s.QuoteOut(text=text, author=author)
