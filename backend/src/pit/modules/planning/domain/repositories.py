from typing import Protocol
from uuid import UUID

from pit.modules.planning.domain.plan import Plan


class PlanRepository(Protocol):
    def add(self, plan: Plan) -> None: ...

    async def get(self, plan_id: UUID) -> Plan | None: ...
