from collections.abc import Mapping
from typing import Any

from pit.modules.challenges.domain.challenge import Category
from pit.modules.challenges.infrastructure.serialization import (
    roadmap_from_json,
    roadmap_to_json,
    schedule_from_json,
    schedule_to_json,
)
from pit.modules.planning.domain.plan import (
    Availability,
    OnboardingAnswers,
    Plan,
    PlanProposal,
    PlanStatus,
)
from pit.modules.planning.infrastructure.tables import plans
from pit.shared.infrastructure.repository import Row, SqlRepository


class SqlPlanRepository(SqlRepository[Plan]):
    table = plans

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
            "proposal": {
                "title": p.title,
                "description": p.description,
                "category": p.category.value,
                "duration_days": p.duration_days,
                "difficulty": p.difficulty,
                "verification_prompt": p.verification_prompt,
                "schedule": schedule_to_json(p.schedule),
                "roadmap": roadmap_to_json(p.roadmap),
            },
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
            proposal=PlanProposal(
                title=p["title"],
                description=p["description"],
                category=Category(p["category"]),
                duration_days=p["duration_days"],
                difficulty=p["difficulty"],
                verification_prompt=p["verification_prompt"],
                schedule=schedule_from_json(p["schedule"]),
                roadmap=roadmap_from_json(p.get("roadmap")),
            ),
            challenge_id=row["challenge_id"],
            participation_id=row["participation_id"],
        )
