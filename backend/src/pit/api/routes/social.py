from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from pit.api import schemas as s
from pit.api import views
from pit.api.deps import ContainerDep, LocaleDep, UserId
from pit.api.ratelimit import rate_limit
from pit.modules.challenges.infrastructure.tables import participations
from pit.modules.coaching.application.commands import MarkNotificationsRead
from pit.modules.coaching.infrastructure.tables import notifications
from pit.modules.identity.application.commands import ChangeLocale
from pit.modules.identity.domain.user import Locale
from pit.modules.identity.infrastructure.tables import users
from pit.modules.moderation.application.commands import FileReport
from pit.modules.moderation.domain.report import ReportReason
from pit.modules.push.application.commands import SubscribePush, UnsubscribePush
from pit.modules.ranking.domain.achievements import Record, badges_for
from pit.modules.ranking.domain.achievements_ru import BADGES_RU
from pit.modules.ranking.domain.scoring import MIN_COHORT_SIZE, period_keys
from pit.shared.application.clock import local_date
from pit.shared.application.lookup import require
from pit.shared.domain.money import Money

router = APIRouter(tags=["me"])

PERIOD_INDEX = {"week": 0, "season": 1, "all": 2}


@router.get("/me", response_model=s.MeOut)
async def me(user_id: UserId, container: ContainerDep, locale: LocaleDep) -> s.MeOut:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        wallet = await uow.wallets.get(user_id)
        points, active, completed, best, unread = await views.user_stats(uow, user_id)
        return s.MeOut(
            id=user.id,
            username=user.username,
            birth_date=user.birth_date,
            birth_year=user.birth_year,
            region_id=user.region_id,
            region_name=await views.region_name(uow, user.region_id, locale),
            phone=user.phone,
            phone_verified=user.phone_verified,
            role=user.role.value,
            wallet=s.WalletBalance(
                available=(wallet.available if wallet else Money.zero()).amount,
                locked=(wallet.locked if wallet else Money.zero()).amount,
            ),
            points=points,
            active_challenges=active,
            completed_challenges=completed,
            best_streak=best,
            unread_notifications=unread,
            telegram_linked=user.telegram_chat_id is not None,
            locale=user.locale.value,
        )


@router.get("/me/notifications", response_model=list[s.NotificationOut])
async def my_notifications(
    user_id: UserId, container: ContainerDep, limit: int = Query(30, le=100)
) -> list[s.NotificationOut]:
    async with container.uow_factory() as uow:
        rows = await uow.session.execute(
            select(notifications)
            .where(notifications.c.user_id == user_id)
            .order_by(notifications.c.sent_at.desc())
            .limit(limit)
        )
        return [
            s.NotificationOut(
                id=row["id"],
                moment=row["moment"],
                title=row["title"],
                body=row["body"],
                created_at=row["sent_at"],
                read=row["read_at"] is not None,
            )
            for row in rows.mappings()
        ]


@router.post("/me/notifications/read", status_code=204)
async def mark_read(body: s.ReadIn, user_id: UserId, container: ContainerDep) -> None:
    await container.bus.handle(
        MarkNotificationsRead(user_id=user_id, notification_ids=tuple(body.ids))
    )


@router.get("/leaderboard", response_model=s.LeaderboardOut, tags=["leaderboard"])
async def leaderboard(
    user_id: UserId,
    container: ContainerDep,
    locale: LocaleDep,
    scope: Literal["global", "age", "region"] = "global",
    period: Literal["week", "season", "all"] = "week",
    limit: int = Query(50, le=100),
) -> s.LeaderboardOut:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        region = await views.region_name(uow, user.region_id, locale)
    today = local_date(container.clock.now(), user.timezone)
    period_key = period_keys(today)[PERIOD_INDEX[period]]
    ru = locale is Locale.RU
    scope_key, title = {
        "global": ("global", "Вся платформа" if ru else "Butun platforma"),
        "age": (
            f"age:{user.birth_year}",
            f"Родившиеся в {user.birth_year}" if ru else f"{user.birth_year}-yilda tug'ilganlar",
        ),
        "region": (f"region:{user.region_id}", region or ("Ваш регион" if ru else "Hududingiz")),
    }[scope]
    key = f"lb:{period_key}:{scope_key}"
    board = container.leaderboard
    size = await board.size(key)
    position = await board.position(key, user_id)
    hidden = scope != "global" and size < MIN_COHORT_SIZE
    entries: list[s.LeaderboardEntry] = []
    if not hidden:
        top = await board.top(key, limit=limit)
        async with container.uow_factory() as uow:
            rows = await uow.session.execute(
                select(users.c.id, users.c.username).where(users.c.id.in_([u for u, _ in top]))
            )
            names = {uid: name for uid, name in rows.tuples()}
        entries = [
            s.LeaderboardEntry(
                rank=i + 1,
                user_id=uid,
                username=names.get(uid, "—"),
                points=points,
                is_me=uid == user_id,
            )
            for i, (uid, points) in enumerate(top)
        ]
    return s.LeaderboardOut(
        scope=scope,
        period=period,
        title=title,
        entries=entries,
        me=s.MyRank(rank=position[0], points=position[1]) if position else None,
        size=size,
        hidden=hidden,
    )


@router.post(
    "/reports",
    response_model=s.IdOut,
    status_code=201,
    tags=["moderation"],
    dependencies=[Depends(rate_limit("report", 10, 24 * 3600, per="user"))],
)
async def report_user(body: s.ReportIn, user_id: UserId, container: ContainerDep) -> s.IdOut:
    report_id = await container.bus.handle(
        FileReport(
            reporter_id=user_id,
            reported_username=body.username,
            reason=ReportReason(body.reason),
            details=body.details,
        )
    )
    return s.IdOut(id=report_id)


@router.get("/me/badges", response_model=list[s.BadgeOut])
async def my_badges(
    user_id: UserId, container: ContainerDep, locale: LocaleDep
) -> list[s.BadgeOut]:
    async with container.uow_factory() as uow:
        user = require(await uow.users.get(user_id), "Foydalanuvchi topilmadi")
        points, _, completed, best, _ = await views.user_stats(uow, user_id)
        runs = await uow.session.execute(
            select(participations.c.id).where(participations.c.user_id == user_id)
        )
        days_done, in_group = 0, False
        for participation_id in runs.scalars():
            run = await uow.participations.get(participation_id)
            if run is not None:
                days_done += run.days_completed
                in_group = in_group or run.group_id is not None
    record = Record(
        days_done=days_done,
        best_streak=best,
        completed_challenges=completed,
        points=points,
        in_group=in_group,
        telegram_linked=user.telegram_chat_id is not None,
    )
    texts = BADGES_RU if locale is Locale.RU else {}
    return [
        s.BadgeOut(
            key=b.key,
            emoji=b.emoji,
            title=texts.get(b.key, (b.title, b.hint))[0],
            hint=texts.get(b.key, (b.title, b.hint))[1],
            earned=earned,
        )
        for b, earned in badges_for(record)
    ]


@router.post(
    "/me/push",
    status_code=204,
    dependencies=[Depends(rate_limit("push", 20, 3600, per="user"))],
)
async def subscribe_push(
    body: s.PushSubscriptionIn, user_id: UserId, container: ContainerDep
) -> None:
    await container.bus.handle(
        SubscribePush(
            user_id=user_id,
            endpoint=body.endpoint,
            p256dh=body.keys.get("p256dh", ""),
            auth=body.keys.get("auth", ""),
        )
    )


@router.delete("/me/push", status_code=204)
async def unsubscribe_push(
    body: s.PushEndpointIn, user_id: UserId, container: ContainerDep
) -> None:
    await container.bus.handle(UnsubscribePush(user_id=user_id, endpoint=body.endpoint))


@router.put("/me/locale", status_code=204)
async def change_locale(body: s.LocaleIn, user_id: UserId, container: ContainerDep) -> None:
    await container.bus.handle(ChangeLocale(user_id=user_id, locale=body.locale))
