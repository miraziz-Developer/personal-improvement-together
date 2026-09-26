import secrets
from typing import Protocol
from uuid import UUID, uuid4

from pit.modules.identity.application.commands import (
    ChangeLocale,
    ConfirmPhone,
    EraseAccount,
    IssueTelegramLink,
    LinkTelegram,
    RegisterUser,
    RegisterWithGoogle,
    RequestPasswordReset,
    RequestPhoneCode,
    ResetPassword,
    SignInWithGoogle,
    UnlinkTelegram,
    VerifyPhoneFromTelegram,
)
from pit.modules.identity.application.ports import (
    GoogleIdentity,
    GoogleVerifier,
    LinkTokens,
    OtpStore,
    PasswordHasher,
    PrivateMessenger,
    SmsSender,
)
from pit.modules.identity.domain.repositories import UserRepository
from pit.modules.identity.domain.user import Locale, User, ensure_strong_password, normalize_phone
from pit.shared.application.clock import Clock, local_date
from pit.shared.application.lookup import require
from pit.shared.application.unit_of_work import Transaction
from pit.shared.domain.errors import DomainError

# Verifying against a real hash when the user does not exist keeps login timing the same,
# so response time does not reveal which usernames exist.
_DUMMY_PASSWORD = "not-a-real-password-1"


class IdentityUoW(Transaction, Protocol):
    @property
    def users(self) -> UserRepository: ...


def new_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _ensure_terms(version: str) -> None:
    if not version:
        raise DomainError("Ro'yxatdan o'tish uchun foydalanish shartlariga rozilik kerak")


async def register_user(
    cmd: RegisterUser, uow: IdentityUoW, *, clock: Clock, hasher: PasswordHasher
) -> UUID:
    ensure_strong_password(cmd.password)
    _ensure_terms(cmd.accepted_terms_version)
    async with uow:
        if await uow.users.get_by_username(cmd.username.strip().lower()):
            raise DomainError("Bu username band, boshqasini tanlang")
        user = User.register(
            user_id=uuid4(),
            username=cmd.username,
            birth_date=cmd.birth_date,
            region_id=cmd.region_id,
            today=local_date(clock.now(), cmd.timezone),
            timezone=cmd.timezone,
            password_hash=hasher.hash(cmd.password),
        )
        user.accept_terms(cmd.accepted_terms_version, clock.now())
        uow.users.add(user)
        await uow.commit()
        return user.id


async def authenticate(
    uow: IdentityUoW, hasher: PasswordHasher, username: str, password: str
) -> User:
    async with uow:
        user = await uow.users.get_by_username(username.strip().lower())
    if user is None or not user.password_hash:
        hasher.verify(password, hasher.hash(_DUMMY_PASSWORD))
        raise DomainError("Username yoki parol noto'g'ri")
    if not hasher.verify(password, user.password_hash):
        raise DomainError("Username yoki parol noto'g'ri")
    return user


async def request_phone_code(
    cmd: RequestPhoneCode, uow: IdentityUoW, *, otp: OtpStore, sms: SmsSender
) -> None:
    phone = normalize_phone(cmd.phone)
    async with uow:
        require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
    code = new_otp_code()
    await otp.put(f"phone:{cmd.user_id}", phone, code)
    await sms.send(phone, f"PIT tasdiqlash kodi: {code}. Kodni hech kimga bermang.")


async def confirm_phone(cmd: ConfirmPhone, uow: IdentityUoW, *, otp: OtpStore) -> None:
    phone = await otp.verify(f"phone:{cmd.user_id}", cmd.code.strip())
    if phone is None:
        raise DomainError("Kod noto'g'ri yoki muddati o'tgan")
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        user.verify_phone(phone)
        await uow.commit()


async def request_password_reset(
    cmd: RequestPasswordReset,
    uow: IdentityUoW,
    *,
    otp: OtpStore,
    sms: SmsSender,
    messenger: PrivateMessenger | None = None,
) -> None:
    """The code goes to the Telegram bot when linked (free, instant), else by SMS to a verified
    phone. Silent when neither exists: the answer must not reveal which usernames exist."""
    async with uow:
        user = await uow.users.get_by_username(cmd.username.strip().lower())
    if user is None:
        return
    code = new_otp_code()
    text = f"PIT parolni tiklash kodi: {code}. Agar siz so'ramagan bo'lsangiz, e'tibor bermang."
    if messenger is not None and user.telegram_chat_id is not None:
        await otp.put(f"reset:{user.id}", user.phone or "", code)
        if await messenger.send(user, f"🔐 {text}"):
            return
    if user.phone_verified and user.phone is not None:
        await otp.put(f"reset:{user.id}", user.phone, code)
        await sms.send(user.phone, text)


async def reset_password(
    cmd: ResetPassword, uow: IdentityUoW, *, otp: OtpStore, hasher: PasswordHasher
) -> None:
    ensure_strong_password(cmd.new_password)
    async with uow:
        user = await uow.users.get_by_username(cmd.username.strip().lower())
        phone = await otp.verify(f"reset:{user.id}", cmd.code.strip()) if user else None
        if user is None or phone is None:
            raise DomainError("Kod noto'g'ri yoki muddati o'tgan")
        user.change_password(hasher.hash(cmd.new_password))
        await uow.commit()


# --- telegram ------------------------------------------------------------------------------


async def issue_telegram_link(
    cmd: IssueTelegramLink, uow: IdentityUoW, *, tokens: LinkTokens
) -> str:
    async with uow:
        require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
    return await tokens.issue(cmd.user_id)


async def link_telegram(cmd: LinkTelegram, uow: IdentityUoW, *, tokens: LinkTokens) -> UUID:
    user_id = await tokens.consume(cmd.token)
    if user_id is None:
        raise DomainError("Havola eskirgan. Saytdagi profilingizdan qaytadan ulang")
    async with uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        # One chat follows one account: linking elsewhere moves it.
        previous = await uow.users.get_by_telegram_chat(cmd.chat_id)
        if previous is not None and previous.id != user.id:
            previous.unlink_telegram()
        user.link_telegram(cmd.chat_id)
        await uow.commit()
    return user.id


async def unlink_telegram(cmd: UnlinkTelegram, uow: IdentityUoW) -> None:
    async with uow:
        if cmd.user_id is not None:
            user = await uow.users.get(cmd.user_id)
        elif cmd.chat_id is not None:
            user = await uow.users.get_by_telegram_chat(cmd.chat_id)
        else:
            raise ValueError("UnlinkTelegram needs user_id or chat_id")
        if user is not None and user.telegram_chat_id is not None:
            user.unlink_telegram()
            await uow.commit()


async def verify_phone_from_telegram(cmd: VerifyPhoneFromTelegram, uow: IdentityUoW) -> str:
    async with uow:
        user = require(await uow.users.get_by_telegram_chat(cmd.chat_id), "Avval Telegram'ni ulang")
        user.verify_phone(cmd.phone)
        await uow.commit()
        return user.phone or ""


# --- google --------------------------------------------------------------------------------


async def sign_in_with_google(
    cmd: SignInWithGoogle, uow: IdentityUoW, *, google: GoogleVerifier
) -> UUID | GoogleIdentity:
    identity = await google.verify(cmd.credential)
    async with uow:
        user = await uow.users.get_by_google_sub(identity.sub)
    return user.id if user is not None else identity


async def register_with_google(cmd: RegisterWithGoogle, uow: IdentityUoW, *, clock: Clock) -> UUID:
    _ensure_terms(cmd.accepted_terms_version)
    async with uow:
        if await uow.users.get_by_google_sub(cmd.google_sub):
            raise DomainError("Bu Google akkaunt allaqachon ro'yxatdan o'tgan. Kirish'ni bosing")
        if await uow.users.get_by_username(cmd.username.strip().lower()):
            raise DomainError("Bu username band, boshqasini tanlang")
        user = User.register(
            user_id=uuid4(),
            username=cmd.username,
            birth_date=cmd.birth_date,
            region_id=cmd.region_id,
            today=local_date(clock.now(), cmd.timezone),
            timezone=cmd.timezone,
        )
        user.connect_google(cmd.google_sub, cmd.email)
        user.accept_terms(cmd.accepted_terms_version, clock.now())
        uow.users.add(user)
        await uow.commit()
        return user.id


async def erase_account(cmd: EraseAccount, uow: IdentityUoW, *, clock: Clock) -> None:
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        if cmd.confirm_username.strip().lower() != user.username:
            raise DomainError("Tasdiqlash uchun username'ingizni aynan yozing")
        user.erase(clock.now())
        await uow.commit()


async def change_locale(cmd: ChangeLocale, uow: IdentityUoW) -> None:
    try:
        locale = Locale(cmd.locale)
    except ValueError:
        raise DomainError("Bunday til yo'q") from None
    async with uow:
        user = require(await uow.users.get(cmd.user_id), "Foydalanuvchi topilmadi")
        user.change_locale(locale)
        await uow.commit()
