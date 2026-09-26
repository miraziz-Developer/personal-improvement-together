from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pit.api.security import read_token
from pit.container import Container

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


async def current_user_id(
    container: ContainerDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> UUID:
    if credentials is None:
        raise HTTPException(401, "Iltimos, tizimga kiring")
    try:
        user_id = read_token(credentials.credentials, container.settings)
    except (jwt.PyJWTError, ValueError, KeyError) as error:
        raise HTTPException(401, "Sessiya muddati tugagan, qayta kiring") from error
    if await container.redis.exists(revoked_key(user_id)):  # the account was erased
        raise HTTPException(401, "Akkaunt o'chirilgan")
    return user_id


def revoked_key(user_id: UUID) -> str:
    return f"revoked:{user_id}"


UserId = Annotated[UUID, Depends(current_user_id)]


async def current_moderator(container: ContainerDep, user_id: UserId) -> UUID:
    async with container.uow_factory() as uow:
        user = await uow.users.get(user_id)
    if user is None or not user.is_moderator:
        raise HTTPException(403, "Bu bo'lim faqat moderatorlar uchun")
    return user_id


ModeratorId = Annotated[UUID, Depends(current_moderator)]
