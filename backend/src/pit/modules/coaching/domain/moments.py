"""The moments the coach speaks up at. Each has phrasings in every supported language."""

from enum import StrEnum


class Moment(StrEnum):
    CHALLENGE_STARTED = "challenge_started"
    DAY_DONE = "day_done"
    STREAK_MILESTONE = "streak_milestone"
    DAY_FROZEN = "day_frozen"
    CHALLENGE_FAILED = "challenge_failed"
    CHALLENGE_COMPLETED = "challenge_completed"
    PROOF_REJECTED = "proof_rejected"
    PROOF_IN_REVIEW = "proof_in_review"
    MORNING = "morning"
    REST_DAY = "rest_day"
    EVENING_REMINDER = "evening_reminder"
    FRIEND_DAY_DONE = "friend_day_done"
    FRIEND_JOINED = "friend_joined"
    FRIEND_BROUGHT = "friend_brought"  # a friend you invited kept going: a thank-you
    WEEKLY_GREAT = "weekly_great"
    WEEKLY_OK = "weekly_ok"
    WEEKLY_TOUGH = "weekly_tough"
    CHEER = "cheer"
    TASK_SOON = "task_soon"  # ten minutes before a timed task: get ready
    TASK_DUE = "task_due"
    MORNING_ROUTINE = "morning_routine"
    MONTH_STARTED = "month_started"
    DAY_SUMMARY = "day_summary"
    FREEZE_REGAINED = "freeze_regained"
