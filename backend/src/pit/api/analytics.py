"""Product analytics for the admin panel: read-only SQL over the whole database.

Erased accounts are left out of the people counts; their anonymous days still count."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pit.api import schemas as s

_PEOPLE = """
SELECT
  count(*) FILTER (WHERE deleted_at IS NULL)                                        AS users,
  count(*) FILTER (WHERE deleted_at IS NULL AND created_at >= :now - interval '7 days')  AS new_7d,
  count(*) FILTER (WHERE deleted_at IS NULL AND created_at >= :now - interval '30 days') AS new_30d,
  count(*) FILTER (WHERE deleted_at IS NULL AND telegram_chat_id IS NOT NULL)       AS telegram,
  count(*) FILTER (WHERE deleted_at IS NULL AND google_sub IS NOT NULL)             AS google
FROM users
"""

_ACTIVE = """
SELECT
  count(DISTINCT user_id) FILTER (WHERE submitted_at >= :now - interval '1 day')   AS dau,
  count(DISTINCT user_id) FILTER (WHERE submitted_at >= :now - interval '7 days')  AS wau,
  count(DISTINCT user_id) FILTER (WHERE submitted_at >= :now - interval '30 days') AS mau
FROM proofs
"""

_FUNNEL = """
SELECT
  (SELECT count(*) FROM users WHERE deleted_at IS NULL)                         AS registered,
  (SELECT count(DISTINCT user_id) FROM participations)                          AS started,
  (SELECT count(DISTINCT user_id) FROM proofs)                                  AS proved,
  (SELECT count(DISTINCT p.user_id) FROM participations p
     JOIN participation_days d ON d.participation_id = p.id AND d.status = 'done') AS day_done,
  (SELECT count(DISTINCT user_id) FROM participations WHERE status = 'completed')  AS completed
"""

# Of the people old enough to be measured, who came back with a proof on day 1 / in week 2?
_RETENTION = """
SELECT
  count(*) FILTER (WHERE u.created_at < :now - interval '2 days')               AS d1_base,
  count(*) FILTER (WHERE u.created_at < :now - interval '2 days' AND EXISTS (
    SELECT 1 FROM proofs pr WHERE pr.user_id = u.id
      AND pr.submitted_at >= u.created_at + interval '1 day'
      AND pr.submitted_at <  u.created_at + interval '2 days'))                 AS d1,
  count(*) FILTER (WHERE u.created_at < :now - interval '14 days')              AS w1_base,
  count(*) FILTER (WHERE u.created_at < :now - interval '14 days' AND EXISTS (
    SELECT 1 FROM proofs pr WHERE pr.user_id = u.id
      AND pr.submitted_at >= u.created_at + interval '7 days'
      AND pr.submitted_at <  u.created_at + interval '14 days'))                AS w1
FROM users u
WHERE u.deleted_at IS NULL
"""

_CHALLENGES = """
SELECT
  count(*) FILTER (WHERE status IN ('scheduled', 'active')) AS running,
  count(*) FILTER (WHERE status = 'completed')              AS completed,
  count(*) FILTER (WHERE status = 'failed')                 AS failed,
  (SELECT count(*) FROM groups)                             AS groups,
  count(*) FILTER (WHERE group_id IS NOT NULL)              AS in_groups
FROM participations
"""

_PROOFS = """
SELECT
  count(*)                                              AS total,
  count(*) FILTER (WHERE status = 'approved')           AS approved,
  count(*) FILTER (WHERE status = 'rejected')           AS rejected,
  count(*) FILTER (WHERE ai_model = 'fallback')         AS unchecked,
  count(*) FILTER (WHERE ai_unsafe)                     AS unsafe,
  (SELECT count(*) FROM proofs WHERE status = 'needs_review') AS in_review
FROM proofs
WHERE submitted_at >= :now - interval '30 days'
"""

_DAILY = """
SELECT day::date AS day,
  (SELECT count(*) FROM users u WHERE u.created_at::date = day::date)           AS signups,
  (SELECT count(DISTINCT pr.user_id) FROM proofs pr
     WHERE pr.submitted_at::date = day::date)                                   AS active
FROM generate_series(
  CAST(:now - interval '29 days' AS date), CAST(:now AS date), interval '1 day'
) AS day
ORDER BY day
"""


async def _row(session: AsyncSession, sql: str, now: datetime) -> dict[str, Any]:
    return dict((await session.execute(text(sql), {"now": now})).mappings().one())


def _share(part: int, base: int) -> float | None:
    return round(part / base, 3) if base else None


async def collect(session: AsyncSession, now: datetime) -> s.AnalyticsOut:
    people = await _row(session, _PEOPLE, now)
    active = await _row(session, _ACTIVE, now)
    funnel = await _row(session, _FUNNEL, now)
    retention = await _row(session, _RETENTION, now)
    runs = await _row(session, _CHALLENGES, now)
    proofs = await _row(session, _PROOFS, now)
    daily = (await session.execute(text(_DAILY), {"now": now})).mappings().all()
    finished = runs["completed"] + runs["failed"]
    return s.AnalyticsOut(
        users=people["users"],
        new_7d=people["new_7d"],
        new_30d=people["new_30d"],
        telegram_share=_share(people["telegram"], people["users"]),
        google_share=_share(people["google"], people["users"]),
        dau=active["dau"],
        wau=active["wau"],
        mau=active["mau"],
        funnel=[
            s.FunnelStep(label="Ro'yxatdan o'tdi", count=funnel["registered"]),
            s.FunnelStep(label="Challenge boshladi", count=funnel["started"]),
            s.FunnelStep(label="Isbot yubordi", count=funnel["proved"]),
            s.FunnelStep(label="Kunni bajardi", count=funnel["day_done"]),
            s.FunnelStep(label="Challenge'ni yakunladi", count=funnel["completed"]),
        ],
        retention_d1=_share(retention["d1"], retention["d1_base"]),
        retention_w1=_share(retention["w1"], retention["w1_base"]),
        running=runs["running"],
        completion_rate=_share(runs["completed"], finished),
        groups=runs["groups"],
        in_groups=runs["in_groups"],
        proofs_30d=proofs["total"],
        approval_rate=_share(proofs["approved"], proofs["approved"] + proofs["rejected"]),
        unchecked_30d=proofs["unchecked"],
        unsafe_30d=proofs["unsafe"],
        in_review=proofs["in_review"],
        daily=[
            s.DailyPoint(day=row["day"], signups=row["signups"], active=row["active"])
            for row in daily
        ],
    )
