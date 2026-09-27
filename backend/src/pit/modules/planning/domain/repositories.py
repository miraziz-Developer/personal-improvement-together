from typing import Protocol
from uuid import UUID

from pit.modules.planning.domain.life_plan import LifePlan
from pit.modules.planning.domain.plan import Plan


class PlanRepository(Protocol):
    def add(self, plan: Plan) -> None: ...

    async def get(self, plan_id: UUID) -> Plan | None: ...

    async def delete_for_user(self, user_id: UUID) -> None: ...


class LifePlanRepository(Protocol):
    def add(self, plan: LifePlan) -> None: ...

    async def get(self, plan_id: UUID) -> LifePlan | None: ...

    async def latest_started(self, user_id: UUID) -> LifePlan | None:
        """The routine the user lives by now (its day frame shapes the daily timeline)."""
        ...

    async def delete_for_user(self, user_id: UUID) -> None: ...
