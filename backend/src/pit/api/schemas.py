"""HTTP contract (request/response models). Kept separate from the domain on purpose."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from pit.modules.challenges.domain.challenge import ParticipationMode
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec

# --- shared ------------------------------------------------------------------------------


class TaskIO(BaseModel):
    key: str
    title: str
    minutes: int
    required: bool = True


Week = list[list[TaskIO]]  # 7 lists, index 0 = Monday


def week_to_schedule(week: Week) -> Schedule:
    return Schedule(
        week=tuple(
            tuple(
                TaskSpec(key=t.key, title=t.title, minutes=t.minutes, required=t.required)
                for t in day
            )
            for day in week
        )
    )


def schedule_to_week(schedule: Schedule) -> Week:
    return [
        [TaskIO(key=t.key, title=t.title, minutes=t.minutes, required=t.required) for t in day]
        for day in schedule.week
    ]


class IdOut(BaseModel):
    id: UUID


# --- auth & profile ----------------------------------------------------------------------


class RegisterIn(BaseModel):
    username: str
    password: str = Field(repr=False)
    birth_date: date
    region_id: UUID
    accepted_terms_version: str = ""


class LoginIn(BaseModel):
    username: str
    password: str = Field(repr=False)


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user_id: UUID


class GoogleIn(BaseModel):
    credential: str = Field(repr=False)  # the ID token from Google Identity Services


class GoogleOut(BaseModel):
    """Either signed in (access_token) or a new user who must finish their profile."""

    access_token: str | None = None
    user_id: UUID | None = None
    signup_token: str | None = None
    email: str | None = None
    suggested_username: str | None = None


class GoogleRegisterIn(BaseModel):
    signup_token: str = Field(repr=False)
    username: str
    birth_date: date
    region_id: UUID
    accepted_terms_version: str = ""


class EraseIn(BaseModel):
    username: str  # typed again to confirm


class ForgotIn(BaseModel):
    username: str


class ResetIn(BaseModel):
    username: str
    code: str = Field(repr=False)
    new_password: str = Field(repr=False)


class PhoneRequestIn(BaseModel):
    phone: str


class PhoneConfirmIn(BaseModel):
    code: str = Field(repr=False)


class RegionOut(BaseModel):
    id: UUID
    name_uz: str
    name_ru: str


class QuoteOut(BaseModel):
    text: str
    author: str


class WalletBalance(BaseModel):
    available: int
    locked: int


class MeOut(BaseModel):
    id: UUID
    username: str
    birth_date: date
    birth_year: int
    region_id: UUID
    region_name: str
    phone: str | None
    phone_verified: bool
    role: str
    wallet: WalletBalance
    points: int
    active_challenges: int
    completed_challenges: int
    best_streak: int
    unread_notifications: int
    telegram_linked: bool


class TelegramLinkOut(BaseModel):
    url: str  # t.me deep link with a one-time token, valid for 10 minutes


# --- challenges --------------------------------------------------------------------------


class ChallengeOut(BaseModel):
    id: UUID
    title: str
    description: str
    category: str
    duration_days: int
    difficulty: int
    proof_types: list[str]
    stake_allowed: bool
    min_stake: int
    max_stake: int
    days_per_week: int
    minutes_per_week: int
    participants: int
    week: Week


class JoinIn(BaseModel):
    mode: ParticipationMode
    stake_amount: int = 0
    start_date: date | None = None
    week: Week | None = None


class DayOut(BaseModel):
    date: date
    status: str


class TaskTodayOut(TaskIO):
    proof_status: str | None
    reason: str | None


class TodayOut(BaseModel):
    date: date
    is_rest_day: bool
    status: str | None
    tasks: list[TaskTodayOut]
    daily_code: str | None


class ParticipationOut(BaseModel):
    id: UUID
    challenge_id: UUID
    title: str
    category: str
    status: str
    mode: str
    stake: int
    start_date: date
    end_date: date
    days_completed: int
    total_days: int
    current_streak: int
    best_streak: int
    freezes_left: int
    today_status: str | None


class ParticipationDetailOut(ParticipationOut):
    calendar: list[DayOut]
    today: TodayOut
    week: Week
    can_cancel: bool


class ScheduleIn(BaseModel):
    week: Week


class ProofOut(BaseModel):
    id: UUID
    status: str
    task_key: str
    for_date: date
    reason: str | None
    reviewed_by_human: bool


# --- plans -------------------------------------------------------------------------------


class AnswersIn(BaseModel):
    goal: str
    motivation: str = ""
    current_level: str = ""
    obstacles: str = ""
    availability: list[int] = Field(min_length=7, max_length=7)  # free minutes, Monday first


class PlanOut(BaseModel):
    id: UUID
    status: str
    title: str
    description: str
    category: str
    duration_days: int
    difficulty: int
    verification_prompt: str
    week: Week
    budgets: list[int]
    participation_id: UUID | None


class StartIn(BaseModel):
    mode: ParticipationMode
    stake_amount: int = 0
    start_date: date | None = None


# --- social ------------------------------------------------------------------------------


class NotificationOut(BaseModel):
    id: UUID
    moment: str
    title: str
    body: str
    created_at: datetime
    read: bool


class ReadIn(BaseModel):
    ids: list[UUID]


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    username: str
    points: int
    is_me: bool


class MyRank(BaseModel):
    rank: int
    points: int


class LeaderboardOut(BaseModel):
    scope: str
    period: str
    title: str
    entries: list[LeaderboardEntry]
    me: MyRank | None
    size: int
    hidden: bool  # small cohorts are hidden to protect privacy


# --- wallet & admin ----------------------------------------------------------------------


class TransactionOut(BaseModel):
    id: UUID
    kind: str
    amount: int
    created_at: datetime


class WalletOut(WalletBalance):
    transactions: list[TransactionOut]


class DepositIn(BaseModel):
    amount: int = Field(gt=0, le=10_000_000)


class ReviewItemOut(BaseModel):
    proof_id: UUID
    username: str
    challenge_title: str
    task_key: str
    for_date: date
    text_note: str | None
    image_url: str | None
    ai_reason: str | None
    ai_confidence: float | None
    stake: int
    flagged: bool  # AI suspects harmful content: look at this one first


class ReviewIn(BaseModel):
    approved: bool
    note: str = ""


class ReportIn(BaseModel):
    username: str
    reason: Literal["abuse", "bad_name", "spam", "other"]
    details: str = Field("", max_length=500)


class ReportOut(BaseModel):
    id: UUID
    reporter: str
    reported: str
    reason: str
    details: str
    created_at: datetime
    reports_against: int  # open reports about the same person: many = act first


class ResolveReportIn(BaseModel):
    action: Literal["dismiss", "reset_username"]


# --- together (groups) ---------------------------------------------------------------------


class GroupInviteOut(BaseModel):
    invite_code: str


class GroupPreviewOut(BaseModel):
    """What the invite link shows before joining — also to people without an account."""

    invite_code: str
    challenge_title: str
    challenge_description: str
    category: str
    duration_days: int
    owner: str
    members: int
    is_full: bool
    week: Week


class GroupMemberOut(BaseModel):
    username: str
    is_me: bool
    is_owner: bool
    status: str
    today_status: str | None  # pending / done / ... ; None = rest day or not started
    current_streak: int
    best_streak: int
    days_completed: int
    total_days: int


class BadgeOut(BaseModel):
    key: str
    emoji: str
    title: str
    hint: str
    earned: bool


class CheerIn(BaseModel):
    username: str
    emoji: str = "👏"


class GroupBoardOut(BaseModel):
    invite_code: str
    members: list[GroupMemberOut]  # best first: most days done, then the longest streak


# --- analytics -----------------------------------------------------------------------------


class FunnelStep(BaseModel):
    label: str
    count: int


class DailyPoint(BaseModel):
    day: date
    signups: int
    active: int  # people who sent at least one proof that day


class AnalyticsOut(BaseModel):
    users: int
    new_7d: int
    new_30d: int
    telegram_share: float | None  # None: nobody to measure yet
    google_share: float | None
    dau: int
    wau: int
    mau: int
    funnel: list[FunnelStep]
    retention_d1: float | None  # came back with a proof the day after signing up
    retention_w1: float | None  # ...and in their second week
    running: int
    completion_rate: float | None  # completed / (completed + failed)
    groups: int
    in_groups: int
    proofs_30d: int
    approval_rate: float | None
    unchecked_30d: int  # approved without an AI check (the AI was down): watch this
    unsafe_30d: int
    in_review: int
    daily: list[DailyPoint]
