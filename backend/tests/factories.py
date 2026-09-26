from uuid import uuid4

from pit.modules.challenges.domain.challenge import Category, Challenge, ProofType, StakePolicy
from pit.modules.challenges.domain.schedule import Schedule, TaskSpec
from pit.modules.planning.domain.plan import Availability, OnboardingAnswers

DAILY_HOUR = Schedule.every_day(TaskSpec(key="main", title="Sport zali", minutes=60))

# Weekdays 2h free, Saturday 4h, Sunday nothing -> plan budgets 96 / 192 / 0 minutes.
AVAILABILITY = Availability.from_mapping({0: 120, 1: 120, 2: 120, 3: 120, 4: 120, 5: 240})
ANSWERS = OnboardingAnswers(
    goal="3 oyda backend dasturchi bo'lish",
    motivation="Yaxshi ishga kirish",
    current_level="Python asoslarini bilaman",
    obstacles="Ish, charchoq",
    availability=AVAILABILITY,
)


def make_challenge(
    *,
    duration_days: int = 7,
    difficulty: int = 2,
    proof_types: frozenset[ProofType] = frozenset({ProofType.PHOTO, ProofType.TEXT}),
    stake_allowed: bool = True,
    schedule: Schedule = DAILY_HOUR,
) -> Challenge:
    return Challenge.create_template(
        challenge_id=uuid4(),
        title=f"{duration_days} kunlik sport",
        description="Har kuni sport zaliga boring",
        category=Category.SPORT,
        duration_days=duration_days,
        difficulty=difficulty,
        proof_types=proof_types,
        verification_prompt="Rasmda sport zali jihozlari va foydalanuvchi ko'rinishi kerak",
        stake_policy=StakePolicy(allowed=stake_allowed),
        default_schedule=schedule,
    )
