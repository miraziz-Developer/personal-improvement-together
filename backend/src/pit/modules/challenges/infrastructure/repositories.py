from collections.abc import Mapping
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from pit.modules.challenges.domain.challenge import (
    ApprovalStatus,
    Category,
    Challenge,
    ParticipationMode,
    ProofType,
    StakePolicy,
)
from pit.modules.challenges.domain.group import Group
from pit.modules.challenges.domain.group_message import GroupMessage
from pit.modules.challenges.domain.participation import (
    OPEN_STATUSES,
    DayStatus,
    Participation,
    ParticipationStatus,
)
from pit.modules.challenges.infrastructure.serialization import (
    roadmap_from_json,
    roadmap_to_json,
    schedule_from_json,
    schedule_to_json,
)
from pit.modules.challenges.infrastructure.tables import (
    challenges,
    group_messages,
    groups,
    participation_days,
    participations,
)
from pit.shared.domain.money import Money
from pit.shared.infrastructure.repository import Row, SqlRepository, utc

OPEN = [s.value for s in OPEN_STATUSES]


class SqlChallengeRepository(SqlRepository[Challenge]):
    table = challenges

    def _to_row(self, item: Challenge) -> Row:
        return {
            "id": item.id,
            "title": item.title,
            "description": item.description,
            "category": item.category.value,
            "duration_days": item.duration_days,
            "difficulty": item.difficulty,
            "proof_types": sorted(p.value for p in item.proof_types),
            "verification_prompt": item.verification_prompt,
            "stake_allowed": item.stake_policy.allowed,
            "min_stake": item.stake_policy.min_stake.amount,
            "max_stake": item.stake_policy.max_stake.amount,
            "default_schedule": schedule_to_json(item.default_schedule),
            "roadmap": roadmap_to_json(item.roadmap),
            "is_template": item.is_template,
            "approval_status": item.approval_status.value,
            "created_by": item.created_by,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Challenge:
        return Challenge(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=Category(row["category"]),
            duration_days=row["duration_days"],
            difficulty=row["difficulty"],
            proof_types=frozenset(ProofType(p) for p in row["proof_types"]),
            verification_prompt=row["verification_prompt"],
            stake_policy=StakePolicy(
                allowed=row["stake_allowed"],
                min_stake=Money(row["min_stake"]),
                max_stake=Money(row["max_stake"]),
            ),
            default_schedule=schedule_from_json(row["default_schedule"]),
            is_template=row["is_template"],
            approval_status=ApprovalStatus(row["approval_status"]),
            created_by=row["created_by"],
            roadmap=roadmap_from_json(row["roadmap"]),
        )


class SqlParticipationRepository(SqlRepository[Participation]):
    table = participations

    def _to_row(self, item: Participation) -> Row:
        return {
            "id": item.id,
            "user_id": item.user_id,
            "challenge_id": item.challenge_id,
            "mode": item.mode.value,
            "stake": item.stake.amount,
            "difficulty": item.difficulty,
            "start_date": item.start_date,
            "duration_days": item.duration_days,
            "status": item.status.value,
            "schedule_history": [
                {"since": since.isoformat(), "week": schedule_to_json(schedule)}
                for since, schedule in item.schedule_history
            ],
            "freezes_total": item.freezes_total,
            "freezes_used": item.freezes_used,
            "paused_days": item.paused_days,
            "current_streak": item.current_streak,
            "best_streak": item.best_streak,
            "group_id": item.group_id,
            "finished_on": item.finished_on,
        }

    def _children(self, item: Participation) -> dict[date, DayStatus]:
        return dict(item.days)

    async def _save_children(self, item: Participation) -> None:
        await self._replace_children(
            participation_days,
            "participation_id",
            item.id,
            [
                {"participation_id": item.id, "day": day, "status": status.value}
                for day, status in item.days.items()
            ],
        )

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Participation:
        day_rows = await self._session.execute(
            select(participation_days.c.day, participation_days.c.status)
            .where(participation_days.c.participation_id == row["id"])
            .order_by(participation_days.c.day)
        )
        return Participation(
            id=row["id"],
            user_id=row["user_id"],
            challenge_id=row["challenge_id"],
            mode=ParticipationMode(row["mode"]),
            stake=Money(row["stake"]),
            difficulty=row["difficulty"],
            start_date=row["start_date"],
            duration_days=row["duration_days"],
            status=ParticipationStatus(row["status"]),
            schedule_history=[
                (date.fromisoformat(entry["since"]), schedule_from_json(entry["week"]))
                for entry in row["schedule_history"]
            ],
            days={day: DayStatus(status) for day, status in day_rows},
            freezes_total=row["freezes_total"],
            freezes_used=row["freezes_used"],
            paused_days=row["paused_days"],
            current_streak=row["current_streak"],
            best_streak=row["best_streak"],
            group_id=row["group_id"],
            finished_on=row["finished_on"],
        )

    async def has_open(self, user_id: UUID, challenge_id: UUID) -> bool:
        if self._pending(lambda p: p.user_id == user_id and p.challenge_id == challenge_id):
            return True
        return await self._exists(
            participations.c.user_id == user_id,
            participations.c.challenge_id == challenge_id,
            participations.c.status.in_(OPEN),
        )

    async def count_open_stakes(self, user_id: UUID) -> int:
        query = select(func.count()).where(
            participations.c.user_id == user_id,
            participations.c.status.in_(OPEN),
            participations.c.mode == ParticipationMode.STAKE.value,
        )
        in_db: int = (await self._session.execute(query)).scalar_one()
        return in_db + len(self._pending(lambda p: p.user_id == user_id and p.is_stake))

    async def list_in_group(self, group_id: UUID) -> list[UUID]:
        query = (
            select(participations.c.id)
            .where(participations.c.group_id == group_id)
            .order_by(participations.c.created_at)
        )
        return list((await self._session.execute(query)).scalars())

    async def list_open_ids(self, user_id: UUID | None = None) -> list[UUID]:
        query = select(participations.c.id).where(participations.c.status.in_(OPEN))
        if user_id is not None:
            query = query.where(participations.c.user_id == user_id)
        query = query.order_by(participations.c.created_at)
        return list((await self._session.execute(query)).scalars())


class SqlGroupRepository(SqlRepository[Group]):
    table = groups

    def _to_row(self, item: Group) -> Row:
        return {
            "id": item.id,
            "challenge_id": item.challenge_id,
            "owner_id": item.owner_id,
            "invite_code": item.invite_code,
            "schedule": schedule_to_json(item.schedule),
            "member_ids": [str(member) for member in item.member_ids],
            "created_at": item.created_at,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Group:
        return Group(
            id=row["id"],
            challenge_id=row["challenge_id"],
            owner_id=row["owner_id"],
            invite_code=row["invite_code"],
            schedule=schedule_from_json(row["schedule"]),
            created_at=row["created_at"],
            member_ids=[UUID(member) for member in row["member_ids"]],
        )

    async def get_by_code(self, invite_code: str) -> Group | None:
        pending = self._pending(lambda g: g.invite_code == invite_code)
        if pending:
            return pending[0]
        found = await self._select(groups.c.invite_code == invite_code)
        return found[0] if found else None


class SqlGroupMessages:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: GroupMessage) -> None:
        await self._session.execute(
            insert(group_messages).values(
                id=message.id,
                group_id=message.group_id,
                user_id=message.user_id,
                text=message.text,
                created_at=message.created_at,
            )
        )

    async def recent(self, group_id: UUID, limit: int) -> list[GroupMessage]:
        rows = await self._session.execute(
            select(group_messages)
            .where(group_messages.c.group_id == group_id)
            .order_by(group_messages.c.created_at.desc())
            .limit(limit)
        )
        return [
            GroupMessage(
                id=row["id"],
                group_id=row["group_id"],
                user_id=row["user_id"],
                text=row["text"],
                created_at=utc(row["created_at"]),
            )
            for row in reversed(rows.mappings().all())
        ]

    async def delete_for_user(self, user_id: UUID) -> None:
        await self._session.execute(
            delete(group_messages).where(group_messages.c.user_id == user_id)
        )
