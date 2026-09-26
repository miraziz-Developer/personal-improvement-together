from collections.abc import Mapping
from typing import Any

from pit.modules.identity.domain.user import Role, User
from pit.modules.identity.infrastructure.tables import users
from pit.shared.infrastructure.repository import Row, SqlRepository


class SqlUserRepository(SqlRepository[User]):
    table = users

    def _to_row(self, item: User) -> Row:
        return {
            "id": item.id,
            "username": item.username,
            "birth_date": item.birth_date,
            "region_id": item.region_id,
            "timezone": item.timezone,
            "phone": item.phone,
            "phone_verified": item.phone_verified,
            "role": item.role.value,
            "password_hash": item.password_hash,
            "terms_version": item.terms_version,
            "terms_accepted_at": item.terms_accepted_at,
            "telegram_chat_id": item.telegram_chat_id,
            "google_sub": item.google_sub,
            "email": item.email,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            birth_date=row["birth_date"],
            region_id=row["region_id"],
            timezone=row["timezone"],
            phone=row["phone"],
            phone_verified=row["phone_verified"],
            role=Role(row["role"]),
            password_hash=row["password_hash"],
            terms_version=row["terms_version"],
            terms_accepted_at=row["terms_accepted_at"],
            telegram_chat_id=row["telegram_chat_id"],
            google_sub=row["google_sub"],
            email=row["email"],
        )

    async def get_by_username(self, username: str) -> User | None:
        pending = self._pending(lambda u: u.username == username)
        if pending:
            return pending[0]
        found = await self._select(users.c.username == username)
        return found[0] if found else None

    async def get_by_telegram_chat(self, chat_id: int) -> User | None:
        pending = self._pending(lambda u: u.telegram_chat_id == chat_id)
        if pending:
            return pending[0]
        found = await self._select(users.c.telegram_chat_id == chat_id)
        return found[0] if found else None

    async def get_by_google_sub(self, sub: str) -> User | None:
        pending = self._pending(lambda u: u.google_sub == sub)
        if pending:
            return pending[0]
        found = await self._select(users.c.google_sub == sub)
        return found[0] if found else None
