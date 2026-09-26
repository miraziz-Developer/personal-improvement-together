"""Schedule <-> JSON (stored in JSONB columns; also used by the planning module)."""

from typing import Any

from pit.modules.challenges.domain.schedule import Schedule, TaskSpec

type ScheduleJson = list[list[dict[str, Any]]]


def schedule_to_json(schedule: Schedule) -> ScheduleJson:
    return [
        [
            {"key": t.key, "title": t.title, "minutes": t.minutes, "required": t.required}
            for t in tasks
        ]
        for tasks in schedule.week
    ]


def schedule_from_json(data: ScheduleJson) -> Schedule:
    return Schedule(week=tuple(tuple(TaskSpec(**task) for task in tasks) for tasks in data))
