from typing import Protocol

from pit.modules.planning.domain.plan import OnboardingAnswers, PlanProposal


class PlanGenerator(Protocol):
    """AI adapter: turns onboarding answers into a structured plan (never free text).

    The domain re-checks the result (80% of free time, allowed durations), so a bad
    AI answer is rejected instead of silently overloading the user.
    """

    async def propose(self, answers: OnboardingAnswers) -> PlanProposal: ...
