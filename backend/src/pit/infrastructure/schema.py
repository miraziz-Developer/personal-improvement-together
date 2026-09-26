"""Imports every module's tables so `metadata` is complete (used by Alembic)."""

from pit.modules.challenges.infrastructure import tables as _challenges
from pit.modules.coaching.infrastructure import tables as _coaching
from pit.modules.identity.infrastructure import tables as _identity
from pit.modules.planning.infrastructure import tables as _planning
from pit.modules.ranking.infrastructure import tables as _ranking
from pit.modules.verification.infrastructure import tables as _verification
from pit.modules.wallet.infrastructure import tables as _wallet
from pit.shared.infrastructure.db import metadata

__all__ = ["metadata"]
_ = (_challenges, _coaching, _identity, _planning, _ranking, _verification, _wallet)
