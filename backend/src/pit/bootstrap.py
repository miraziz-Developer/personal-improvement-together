"""Composition root: the only place that knows every module and wires them together."""

from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Any

from pit.modules.challenges.application import handlers as challenges
from pit.modules.challenges.application.commands import (
    CancelParticipation,
    ChangeSchedule,
    CloseDays,
    CreateGroup,
    JoinChallenge,
    JoinGroup,
    LeaveChallenge,
    PauseChallenge,
    RecordTaskApproved,
    RefreshDay,
)
from pit.modules.challenges.domain.events import (
    DayCompleted,
    DayFrozen,
    DayNeedsHumanReview,
    GroupMemberJoined,
    OptionalTaskCompleted,
    ParticipationCancelled,
    ParticipationCompleted,
    ParticipationFailed,
    ParticipationStarted,
)
from pit.modules.coaching.application import handlers as coaching
from pit.modules.coaching.application.commands import (
    CheerFriend,
    MarkNotificationsRead,
    SendDailyNudges,
    SendTaskReminders,
    SendWeeklySummaries,
)
from pit.modules.coaching.application.ports import ChallengeTexts, OwnTexts
from pit.modules.coaching.domain.notification import NotificationCreated
from pit.modules.identity.application import handlers as identity
from pit.modules.identity.application.commands import (
    ChangeLocale,
    ConfirmPhone,
    EraseAccount,
    IssueTelegramLink,
    LinkTelegram,
    RegisterUser,
    RegisterWithGoogle,
    RequestPasswordReset,
    RequestPhoneCode,
    ResetPassword,
    SignInWithGoogle,
    UnlinkTelegram,
    VerifyPhoneFromTelegram,
)
from pit.modules.identity.application.ports import (
    GoogleVerifier,
    LinkTokens,
    OtpStore,
    PasswordHasher,
    SmsSender,
)
from pit.modules.identity.domain.events import AccountErased
from pit.modules.moderation.application import handlers as moderation
from pit.modules.moderation.application.commands import FileReport, ResolveReport
from pit.modules.planning.application import handlers as planning
from pit.modules.planning.application.commands import (
    AddToRoutine,
    ChangeDayFrame,
    DraftLifePlan,
    DraftPlan,
    EditLifePlanGoal,
    EditPlan,
    RetimeLifePlanRun,
    RetimeTasks,
    StartLifePlan,
    StartPlan,
)
from pit.modules.planning.application.ports import LifePlanGenerator, PlanGenerator
from pit.modules.planning.infrastructure.generators import TemplateLifePlanGenerator
from pit.modules.push.application import handlers as push
from pit.modules.push.application.commands import SubscribePush, UnsubscribePush
from pit.modules.push.application.ports import WebPushSender
from pit.modules.ranking.application import handlers as ranking
from pit.modules.ranking.application.ports import LeaderboardIndex
from pit.modules.telegram.application import delivery as telegram
from pit.modules.telegram.application.ports import TelegramApi
from pit.modules.verification.application import handlers as verification
from pit.modules.verification.application.commands import ReviewProof, SubmitProof, VerifyProof
from pit.modules.verification.application.day_evidence import ProofDayEvidenceReader
from pit.modules.verification.application.ports import (
    ProofVerifier,
    StoredFiles,
    VerificationQueue,
)
from pit.modules.verification.domain.events import (
    ProofApproved,
    ProofRejected,
    ProofSentToReview,
    ProofSubmitted,
)
from pit.modules.wallet.application import handlers as wallet
from pit.modules.wallet.application.commands import Deposit
from pit.shared.application.clock import Clock
from pit.shared.application.messagebus import MessageBus
from pit.shared.application.unit_of_work import UnitOfWork


@dataclass(frozen=True)
class Dependencies:
    uow_factory: Callable[[], UnitOfWork]
    clock: Clock
    verifier: ProofVerifier
    verification_queue: VerificationQueue
    leaderboard: LeaderboardIndex
    plan_generator: PlanGenerator
    password_hasher: PasswordHasher
    otp_store: OtpStore
    sms_sender: SmsSender
    link_tokens: LinkTokens
    daily_code_secret: bytes
    stakes_enabled: bool = True  # paid (stake) mode; off while the platform is free
    telegram: TelegramApi | None = None  # None = no bot configured
    web_url: str = ""
    google: GoogleVerifier | None = None  # None = "Sign in with Google" is off
    files: StoredFiles | None = None  # proof photos; needed to erase accounts
    push: WebPushSender | None = None  # None = browser notifications are off
    challenge_texts: ChallengeTexts = field(default_factory=OwnTexts)  # catalog translations
    life_plan_generator: LifePlanGenerator = field(default_factory=TemplateLifePlanGenerator)


def bootstrap(deps: Dependencies, *, strict: bool = False) -> MessageBus:
    clock = deps.clock

    def escrow(uow: Any) -> wallet.WalletStakeEscrow:
        return wallet.WalletStakeEscrow(uow, clock)

    evidence_reader = ProofDayEvidenceReader
    release = partial(wallet.release_stake, clock=clock)
    messenger = telegram.TelegramMessenger(deps.telegram) if deps.telegram else None

    command_handlers: dict[type, Any] = {
        # identity
        RegisterUser: partial(identity.register_user, clock=clock, hasher=deps.password_hasher),
        RequestPhoneCode: partial(
            identity.request_phone_code, otp=deps.otp_store, sms=deps.sms_sender
        ),
        ConfirmPhone: partial(identity.confirm_phone, otp=deps.otp_store),
        RequestPasswordReset: partial(
            identity.request_password_reset,
            otp=deps.otp_store,
            sms=deps.sms_sender,
            messenger=messenger,
        ),
        ResetPassword: partial(
            identity.reset_password, otp=deps.otp_store, hasher=deps.password_hasher
        ),
        IssueTelegramLink: partial(identity.issue_telegram_link, tokens=deps.link_tokens),
        LinkTelegram: partial(identity.link_telegram, tokens=deps.link_tokens),
        UnlinkTelegram: identity.unlink_telegram,
        VerifyPhoneFromTelegram: identity.verify_phone_from_telegram,
        EraseAccount: partial(identity.erase_account, clock=clock),
        ChangeLocale: identity.change_locale,
        RegisterWithGoogle: partial(identity.register_with_google, clock=clock),
        # coaching
        SendDailyNudges: partial(
            coaching.send_daily_nudges, clock=clock, texts=deps.challenge_texts
        ),
        SendTaskReminders: partial(
            coaching.send_task_reminders, clock=clock, texts=deps.challenge_texts
        ),
        MarkNotificationsRead: partial(coaching.mark_read, clock=clock),
        SendWeeklySummaries: partial(coaching.send_weekly_summaries, clock=clock),
        CheerFriend: partial(coaching.cheer_friend, clock=clock),
        # planning — the "make me a plan" path
        DraftPlan: partial(planning.draft_plan, generator=deps.plan_generator),
        EditPlan: planning.edit_plan,
        DraftLifePlan: partial(planning.draft_life_plan, generator=deps.life_plan_generator),
        EditLifePlanGoal: planning.edit_life_plan_goal,
        RetimeLifePlanRun: planning.retime_life_plan_run,
        RetimeTasks: partial(planning.retime_tasks, clock=clock),
        ChangeDayFrame: planning.change_day_frame,
        AddToRoutine: partial(
            planning.add_to_routine,
            clock=clock,
            escrow=escrow,
            stakes_enabled=deps.stakes_enabled,
        ),
        StartLifePlan: partial(
            planning.start_life_plan,
            clock=clock,
            escrow=escrow,
            stakes_enabled=deps.stakes_enabled,
        ),
        StartPlan: partial(
            planning.start_plan, clock=clock, escrow=escrow, stakes_enabled=deps.stakes_enabled
        ),
        # challenges — the "pick a ready-made challenge" path, and the daily calendar
        LeaveChallenge: partial(challenges.leave_challenge, clock=clock),
        PauseChallenge: partial(challenges.pause_challenge, clock=clock),
        JoinChallenge: partial(
            challenges.join_challenge,
            clock=clock,
            escrow=escrow,
            stakes_enabled=deps.stakes_enabled,
        ),
        CancelParticipation: partial(challenges.cancel_participation, clock=clock),
        CreateGroup: partial(challenges.create_group, clock=clock),
        JoinGroup: partial(
            challenges.join_group, clock=clock, escrow=escrow, stakes_enabled=deps.stakes_enabled
        ),
        ChangeSchedule: partial(challenges.change_schedule, clock=clock),
        CloseDays: partial(challenges.close_days, clock=clock, evidence_reader=evidence_reader),
        RefreshDay: partial(challenges.refresh_day, evidence_reader=evidence_reader),
        RecordTaskApproved: partial(
            challenges.record_task_approved, evidence_reader=evidence_reader
        ),
        # verification
        SubmitProof: partial(
            verification.submit_proof, clock=clock, code_secret=deps.daily_code_secret
        ),
        VerifyProof: partial(verification.verify_proof, verifier=deps.verifier),
        ReviewProof: partial(verification.review_proof, clock=clock),
        # wallet
        Deposit: partial(wallet.deposit, clock=clock),
        # push
        SubscribePush: partial(push.subscribe, clock=clock),
        UnsubscribePush: push.unsubscribe,
        # moderation
        FileReport: partial(moderation.file_report, clock=clock),
        ResolveReport: partial(moderation.resolve_report, clock=clock),
    }
    event_handlers: dict[type, list[Any]] = {
        ProofSubmitted: [partial(verification.enqueue_verification, queue=deps.verification_queue)],
        ProofApproved: [verification.task_approved],
        ProofRejected: [
            verification.refresh_day_after_rejection,
            partial(coaching.on_proof_rejected, clock=clock),
        ],
        ProofSentToReview: [partial(coaching.on_proof_in_review, clock=clock)],
        ParticipationStarted: [
            partial(coaching.on_started, clock=clock, texts=deps.challenge_texts)
        ],
        DayFrozen: [partial(coaching.on_day_frozen, clock=clock)],
        DayNeedsHumanReview: [verification.escalate_for_review],
        DayCompleted: [
            partial(ranking.award_day_points, index=deps.leaderboard),
            partial(coaching.on_day_completed, clock=clock),
            partial(coaching.on_friend_day_done, clock=clock),
        ],
        GroupMemberJoined: [
            partial(coaching.on_friend_joined, clock=clock, texts=deps.challenge_texts)
        ],
        # Privacy first: if a later handler fails, the photos and messages are already gone.
        AccountErased: [
            push.forget_subscriptions,
            partial(verification.forget_proofs, files=deps.files),
            coaching.forget_notifications,
            planning.forget_plans,
            partial(ranking.drop_from_leaderboards, index=deps.leaderboard),
            partial(challenges.withdraw_participations, clock=clock),
        ],
        OptionalTaskCompleted: [
            partial(ranking.award_optional_task_points, index=deps.leaderboard)
        ],
        ParticipationCompleted: [
            release,
            partial(ranking.award_completion_bonus, index=deps.leaderboard),
            partial(coaching.on_completed, clock=clock, texts=deps.challenge_texts),
        ],
        ParticipationCancelled: [release],
        ParticipationFailed: [
            partial(wallet.forfeit_stake, clock=clock),
            partial(coaching.on_failed, clock=clock),
        ],
    }
    if deps.google is not None:
        command_handlers[SignInWithGoogle] = partial(
            identity.sign_in_with_google, google=deps.google
        )
    # Delivery channels are best effort: last in each list, never holding up the real work.
    deliveries: list[Any] = []
    if deps.push is not None:
        deliveries.append(partial(push.deliver_push, sender=deps.push))
    if deps.telegram is not None:
        deliveries.append(
            partial(telegram.deliver_notification, telegram=deps.telegram, web_url=deps.web_url)
        )
    if deliveries:
        event_handlers[NotificationCreated] = deliveries
    if deps.telegram is not None:
        event_handlers[ProofApproved].append(
            partial(
                telegram.announce_task_approved,
                telegram=deps.telegram,
                texts=deps.challenge_texts,
            )
        )
    return MessageBus(deps.uow_factory, command_handlers, event_handlers, strict=strict)
