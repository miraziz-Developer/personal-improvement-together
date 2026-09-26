from celery import Celery
from celery.schedules import crontab

from pit.config import Settings


def make_celery(settings: Settings) -> Celery:
    app = Celery("pit", broker=settings.redis_url)
    app.conf.update(
        timezone="Asia/Tashkent",
        task_acks_late=True,  # a crashed worker's task is re-delivered, handlers are idempotent
        worker_prefetch_multiplier=1,
        beat_schedule={
            "close-days": {"task": "pit.close_days", "schedule": crontab(minute=15, hour=0)},
            "morning-nudges": {
                "task": "pit.daily_nudges",
                "schedule": crontab(minute=0, hour=8),
                "args": ("morning",),
            },
            "evening-nudges": {
                "task": "pit.daily_nudges",
                "schedule": crontab(minute=0, hour=20),
                "args": ("evening",),
            },
        },
    )
    return app
