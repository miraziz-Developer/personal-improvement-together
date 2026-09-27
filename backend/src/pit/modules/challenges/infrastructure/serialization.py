"""Schedule <-> JSON (stored in JSONB columns; also used by the planning module)."""

from datetime import time
from typing import Any

from pit.modules.challenges.domain.roadmap import Milestone, Roadmap
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec

type ScheduleJson = list[list[dict[str, Any]]]


def _task_to_json(task: TaskSpec) -> dict[str, Any]:
    data: dict[str, Any] = {
        "key": task.key,
        "title": task.title,
        "minutes": task.minutes,
        "required": task.required,
    }
    if task.at is not None:
        data["at"] = task.at.strftime("%H:%M")
    return data


def _task_from_json(data: dict[str, Any]) -> TaskSpec:
    at = data.get("at")
    return TaskSpec(
        key=data["key"],
        title=data["title"],
        minutes=data["minutes"],
        required=data.get("required", True),
        at=time.fromisoformat(at) if at else None,
    )


def schedule_to_json(schedule: Schedule) -> ScheduleJson:
    return [[_task_to_json(t) for t in tasks] for tasks in schedule.week]


def schedule_from_json(data: ScheduleJson) -> Schedule:
    return Schedule(week=tuple(tuple(_task_from_json(task) for task in tasks) for tasks in data))


def roadmap_to_json(roadmap: Roadmap | None) -> dict[str, Any] | None:
    if roadmap is None:
        return None
    return {
        "outcome": roadmap.outcome,
        "weeks": [
            {"theme": w.theme, "goal": w.goal, "lessons": list(w.lessons)} for w in roadmap.weeks
        ],
    }


def roadmap_from_json(data: dict[str, Any] | None) -> Roadmap | None:
    if not data:
        return None
    return Roadmap(
        outcome=data["outcome"],
        weeks=tuple(
            Milestone(theme=w["theme"], goal=w["goal"], lessons=tuple(w.get("lessons", ())))
            for w in data["weeks"]
        ),
    )
