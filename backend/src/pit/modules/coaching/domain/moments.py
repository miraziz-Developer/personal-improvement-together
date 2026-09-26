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
    WEEKLY_GREAT = "weekly_great"
    WEEKLY_OK = "weekly_ok"
    WEEKLY_TOUGH = "weekly_tough"
    CHEER = "cheer"
