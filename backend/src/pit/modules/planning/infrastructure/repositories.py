from collections.abc import Mapping
from datetime import time
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select

from pit.modules.challenges.domain.challenge import Category
from pit.modules.challenges.infrastructure.serialization import (
    roadmap_from_json,
    roadmap_to_json,
    schedule_from_json,
    schedule_to_json,
)
from pit.modules.planning.domain.life_plan import ExistingRun, GoalAnswers, LifeGoal, LifePlan
from pit.modules.planning.domain.plan import (
    Availability,
    OnboardingAnswers,
    Plan,
    PlanProposal,
    PlanStatus,
)
from pit.modules.planning.domain.routine import BusyBlock, DayFrame
from pit.modules.planning.infrastructure.tables import life_plans, plans
from pit.shared.infrastructure.repository import Row, SqlRepository


def proposal_to_json(p: PlanProposal) -> dict[str, Any]:
    return {
        "title": p.title,
        "description": p.description,
        "category": p.category.value,
        "duration_days": p.duration_days,
        "difficulty": p.difficulty,
        "verification_prompt": p.verification_prompt,
        "schedule": schedule_to_json(p.schedule),
        "roadmap": roadmap_to_json(p.roadmap),
    }


def proposal_from_json(p: Mapping[str, Any]) -> PlanProposal:
    return PlanProposal(
        title=p["title"],
        description=p["description"],
        category=Category(p["category"]),
        duration_days=p["duration_days"],
        difficulty=p["difficulty"],
        verification_prompt=p["verification_prompt"],
        schedule=schedule_from_json(p["schedule"]),
        roadmap=roadmap_from_json(p.get("roadmap")),
    )


def frame_to_json(frame: DayFrame) -> dict[str, Any]:
    return {
        "wake": frame.wake.strftime("%H:%M"),
        "sleep": frame.sleep.strftime("%H:%M"),
        "busy": [
            {
                "label": b.label,
                "weekdays": sorted(b.weekdays),
                "start": b.start.strftime("%H:%M"),
                "end": b.end.strftime("%H:%M"),
            }
            for b in frame.busy
        ],
    }


def frame_from_json(data: Mapping[str, Any]) -> DayFrame:
    return DayFrame(
        wake=time.fromisoformat(data["wake"]),
        sleep=time.fromisoformat(data["sleep"]),
        busy=tuple(
            BusyBlock(
                label=b["label"],
                weekdays=frozenset(b["weekdays"]),
                start=time.fromisoformat(b["start"]),
                end=time.fromisoformat(b["end"]),
            )
            for b in data["busy"]
        ),
    )


class SqlPlanRepository(SqlRepository[Plan]):
    table = plans

    async def delete_for_user(self, user_id: UUID) -> None:
        await self._session.execute(delete(plans).where(plans.c.user_id == user_id))

    def _to_row(self, item: Plan) -> Row:
        a, p = item.answers, item.proposal
        return {
            "id": item.id,
            "user_id": item.user_id,
            "status": item.status.value,
            "answers": {
                "goal": a.goal,
                "motivation": a.motivation,
                "current_level": a.current_level,
                "obstacles": a.obstacles,
                "availability": list(a.availability.minutes_by_weekday),
                "language": a.language,
            },
            "proposal": proposal_to_json(p),
            "challenge_id": item.challenge_id,
            "participation_id": item.participation_id,
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> Plan:
        a, p = row["answers"], row["proposal"]
        return Plan(
            id=row["id"],
            user_id=row["user_id"],
            status=PlanStatus(row["status"]),
            answers=OnboardingAnswers(
                goal=a["goal"],
                motivation=a["motivation"],
                current_level=a["current_level"],
                obstacles=a["obstacles"],
                availability=Availability(minutes_by_weekday=tuple(a["availability"])),
                language=a.get("language", "uz"),
            ),
            proposal=proposal_from_json(p),
            challenge_id=row["challenge_id"],
            participation_id=row["participation_id"],
        )


class SqlLifePlanRepository(SqlRepository[LifePlan]):
    table = life_plans

    def _to_row(self, item: LifePlan) -> Row:
        return {
            "id": item.id,
            "user_id": item.user_id,
            "status": item.status.value,
            "language": item.language,
            "duration_days": item.duration_days,
            "frame": frame_to_json(item.frame),
            "goals": [
                {
                    "key": g.key,
                    "goal": g.answers.goal,
                    "motivation": g.answers.motivation,
                    "current_level": g.answers.current_level,
                    "proposal": proposal_to_json(g.proposal),
                    "challenge_id": str(g.challenge_id) if g.challenge_id else None,
                    "participation_id": str(g.participation_id) if g.participation_id else None,
                }
                for g in item.goals
            ],
            "existing": [
                {
                    "participation_id": str(e.participation_id),
                    "challenge_id": str(e.challenge_id),
                    "title": e.title,
                    "category": e.category.value,
                    "schedule": schedule_to_json(e.schedule),
                }
                for e in item.existing
            ],
        }

    async def _to_aggregate(self, row: Mapping[str, Any]) -> LifePlan:
        return LifePlan(
            id=row["id"],
            user_id=row["user_id"],
            status=PlanStatus(row["status"]),
            language=row["language"],
            duration_days=row["duration_days"],
            frame=frame_from_json(row["frame"]),
            goals=tuple(
                LifeGoal(
                    key=g["key"],
                    answers=GoalAnswers(
                        goal=g["goal"], motivation=g["motivation"], current_level=g["current_level"]
                    ),
                    proposal=proposal_from_json(g["proposal"]),
                    challenge_id=UUID(g["challenge_id"]) if g["challenge_id"] else None,
                    participation_id=UUID(g["participation_id"]) if g["participation_id"] else None,
                )
                for g in row["goals"]
            ),
            existing=tuple(
                ExistingRun(
                    participation_id=UUID(e["participation_id"]),
                    challenge_id=UUID(e["challenge_id"]),
                    title=e["title"],
                    category=Category(e["category"]),
                    schedule=schedule_from_json(e["schedule"]),
                )
                for e in row["existing"] or []
            ),
        )

    async def latest_started(self, user_id: UUID) -> LifePlan | None:
        row = (
            (
                await self._session.execute(
                    select(life_plans)
                    .where(
                        life_plans.c.user_id == user_id,
                        life_plans.c.status == PlanStatus.STARTED.value,
                    )
                    .order_by(life_plans.c.created_at.desc())
                    .limit(1)
                )
            )
            .mappings()
            .first()
        )
        return await self._track(dict(row)) if row else None

    async def delete_for_user(self, user_id: UUID) -> None:
        await self._session.execute(delete(life_plans).where(life_plans.c.user_id == user_id))
