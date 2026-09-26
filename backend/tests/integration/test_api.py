"""The whole product through HTTP, on real Postgres (AI, Redis and S3 replaced by fakes)."""

import io
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import fakeredis
import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import text

from pit.api.app import create_app
from pit.catalog import catalog_id
from pit.cli import make_moderator, seed
from pit.config import Settings
from pit.container import Container, InlineVerificationQueue, build_container
from pit.jobs import requeue_stale_proofs
from pit.modules.identity.application.ports import GoogleIdentity
from pit.modules.identity.domain.user import CURRENT_TERMS_VERSION
from pit.modules.telegram.application.ports import ShareContact
from pit.modules.verification.infrastructure.storage import InMemoryStorage
from tests.fakes import FakeGoogle, FakeSms, FakeTelegram


@dataclass
class Api:
    client: AsyncClient
    container: Container
    sms: FakeSms
    telegram: FakeTelegram
    google: FakeGoogle

    async def settle(self) -> None:
        """Wait for in-process background verification to finish."""
        assert isinstance(self.container.queue, InlineVerificationQueue)
        await self.container.queue.drain()

    async def register(self, username: str = "ali_2008") -> dict[str, str]:
        regions = (await self.client.get("/api/v1/regions")).json()
        tashkent = next(r for r in regions if r["name_uz"] == "Toshkent shahri")
        response = await self.client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "password": "kuchli-parol-1",
                "birth_date": "2008-03-01",
                "region_id": tashkent["id"],
                "accepted_terms_version": CURRENT_TERMS_VERSION,
            },
        )
        assert response.status_code == 201, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def api(migrated_database: str) -> AsyncIterator[Api]:
    settings = Settings(
        database_url=migrated_database,
        daily_code_secret=SecretStr("test-code-secret-0123456789abcdef"),
        jwt_secret=SecretStr("test-jwt-secret-0123456789abcdef0123"),
        storage="memory",
        inline_tasks=True,
        ai_providers="",  # never call a real AI from tests, whatever backend/.env says
        env="local",
        stakes_enabled=True,
        telegram_bot_username="pit_test_bot",
        telegram_webhook_secret=SecretStr("hook-secret-0123456789"),
        google_client_id="test-client.apps.googleusercontent.com",
    )
    sms, telegram, google = FakeSms(), FakeTelegram(), FakeGoogle()
    container = build_container(
        settings,
        redis=fakeredis.aioredis.FakeRedis(decode_responses=True),
        storage=InMemoryStorage(),
        sms_sender=sms,
        telegram_api=telegram,
        google=google,
    )
    await seed(container)
    app = create_app(container)
    app.state.container = container  # the test transport does not run the lifespan
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield Api(client, container, sms, telegram, google)
    await container.close()
    async with container.engine.begin() as connection:
        await connection.execute(text("TRUNCATE users, challenges CASCADE"))
    await container.engine.dispose()


def jpeg() -> bytes:
    image = Image.effect_noise((320, 240), 60).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG")
    return buffer.getvalue()


async def test_errors_are_friendly_and_consistent(api: Api) -> None:
    unauthorized = await api.client.get("/api/v1/me")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["message"] == "Iltimos, tizimga kiring"

    wrong = await api.client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "whatever-1"}
    )
    assert wrong.status_code == 422
    assert wrong.json() == {"code": "domain_error", "message": "Username yoki parol noto'g'ri"}


async def test_weak_password_is_refused(api: Api) -> None:
    regions = (await api.client.get("/api/v1/regions")).json()
    response = await api.client.post(
        "/api/v1/auth/register",
        json={
            "username": "zaif",
            "password": "12345678",
            "birth_date": "2010-01-01",
            "region_id": regions[0]["id"],
            "accepted_terms_version": CURRENT_TERMS_VERSION,
        },
    )
    assert response.status_code == 422
    assert "harf" in response.json()["message"]


async def test_full_journey_of_a_stake_challenge(api: Api) -> None:
    auth = await api.register()
    login = await api.client.post(
        "/api/v1/auth/login", json={"username": "ali_2008", "password": "kuchli-parol-1"}
    )
    assert login.status_code == 200

    # Phone: the SMS code confirms the number (required for stake mode)
    await api.client.post(
        "/api/v1/auth/phone/request", json={"phone": "+998 90 123 45 67"}, headers=auth
    )
    code = re.search(r"\d{6}", api.sms.sent[-1][1])
    assert code is not None
    confirmed = await api.client.post(
        "/api/v1/auth/phone/confirm", json={"code": code.group()}, headers=auth
    )
    assert confirmed.status_code == 204

    # Catalog -> money -> join with a stake
    catalog = (await api.client.get("/api/v1/challenges")).json()
    assert len(catalog) == 8
    await api.client.post("/api/v1/wallet/dev-deposit", json={"amount": 150_000}, headers=auth)
    reading = str(catalog_id("reading-30"))
    joined = await api.client.post(
        f"/api/v1/challenges/{reading}/join",
        json={"mode": "stake", "stake_amount": 100_000},
        headers=auth,
    )
    assert joined.status_code == 201, joined.text
    pid = joined.json()["id"]

    detail = (await api.client.get(f"/api/v1/me/participations/{pid}", headers=auth)).json()
    assert detail["today"]["daily_code"]  # stake photos must show today's code
    assert [t["key"] for t in detail["today"]["tasks"]] == ["read", "notes"]

    # Photo proof -> background verification -> the day is done
    uploaded = await api.client.post(
        "/api/v1/proofs",
        data={"participation_id": pid, "task_key": "read"},
        files={"file": ("page.jpg", jpeg(), "image/jpeg")},
        headers=auth,
    )
    assert uploaded.status_code == 201, uploaded.text
    await api.settle()
    proof = (await api.client.get(f"/api/v1/proofs/{uploaded.json()['id']}", headers=auth)).json()
    assert proof["status"] == "approved"
    detail = (await api.client.get(f"/api/v1/me/participations/{pid}", headers=auth)).json()
    assert detail["today"]["status"] == "done"
    assert detail["current_streak"] == 1

    # The coach spoke, points were earned, money is frozen
    me: dict[str, Any] = (await api.client.get("/api/v1/me", headers=auth)).json()
    assert me["phone_verified"] is True
    assert me["wallet"] == {"available": 50_000, "locked": 100_000}
    assert me["points"] > 0
    feed = (await api.client.get("/api/v1/me/notifications", headers=auth)).json()
    moments = {n["moment"] for n in feed}
    assert {"challenge_started", "day_done"} <= moments
    await api.client.post(
        "/api/v1/me/notifications/read", json={"ids": [n["id"] for n in feed]}, headers=auth
    )
    assert (await api.client.get("/api/v1/me", headers=auth)).json()["unread_notifications"] == 0

    # Leaderboards: first place globally; the tiny age cohort stays private
    board = (
        await api.client.get("/api/v1/leaderboard?scope=global&period=week", headers=auth)
    ).json()
    assert board["entries"][0]["is_me"] and board["me"]["rank"] == 1
    cohort = (await api.client.get("/api/v1/leaderboard?scope=age", headers=auth)).json()
    assert cohort["hidden"] is True and cohort["title"] == "2008-yilda tug'ilganlar"

    wallet = (await api.client.get("/api/v1/wallet", headers=auth)).json()
    assert [t["kind"] for t in wallet["transactions"]] == ["stake_lock", "deposit"]


async def test_onboarding_plan_path(api: Api) -> None:
    auth = await api.register("plan_user")
    plan = await api.client.post(
        "/api/v1/plans",
        json={
            "goal": "Python backend dasturchi bo'lish",
            "motivation": "Yaxshi ish",
            "current_level": "Boshlang'ich",
            "obstacles": "Vaqt kam",
            "availability": [90, 90, 90, 90, 90, 180, 0],
        },
        headers=auth,
    )
    assert plan.status_code == 201, plan.text
    body = plan.json()
    assert body["category"] == "code"
    assert body["week"][6] == []  # no free time on Sunday -> rest day
    assert all(
        sum(t["minutes"] for t in day) <= b
        for day, b in zip(body["week"], body["budgets"], strict=True)
    )

    started = await api.client.post(
        f"/api/v1/plans/{body['id']}/start", json={"mode": "free"}, headers=auth
    )
    assert started.status_code == 201, started.text
    mine = (await api.client.get("/api/v1/me/participations", headers=auth)).json()
    assert mine[0]["title"].startswith("Python backend dasturchi")


async def test_moderation_is_for_moderators_only(api: Api) -> None:
    auth = await api.register("oddiy")
    assert (await api.client.get("/api/v1/admin/proofs", headers=auth)).status_code == 403

    await make_moderator(api.container, "oddiy")
    queue = await api.client.get("/api/v1/admin/proofs", headers=auth)
    assert queue.status_code == 200 and queue.json() == []


async def test_password_reset_by_sms_without_revealing_accounts(api: Api) -> None:
    auth = await api.register("unutuvchan")
    await api.client.post(
        "/api/v1/auth/phone/request", json={"phone": "+998901112233"}, headers=auth
    )
    phone_code = re.search(r"\d{6}", api.sms.sent[-1][1])
    assert phone_code is not None
    await api.client.post(
        "/api/v1/auth/phone/confirm", json={"code": phone_code.group()}, headers=auth
    )

    unknown = await api.client.post("/api/v1/auth/password/forgot", json={"username": "yoq_odam"})
    assert unknown.status_code == 204  # same answer as for a real account
    sent_before = len(api.sms.sent)
    await api.client.post("/api/v1/auth/password/forgot", json={"username": "unutuvchan"})
    assert len(api.sms.sent) == sent_before + 1
    code = re.search(r"\d{6}", api.sms.sent[-1][1])
    assert code is not None

    wrong = await api.client.post(
        "/api/v1/auth/password/reset",
        json={"username": "unutuvchan", "code": "000000", "new_password": "yangi-parol-7"},
    )
    assert wrong.status_code == 422
    reset = await api.client.post(
        "/api/v1/auth/password/reset",
        json={"username": "unutuvchan", "code": code.group(), "new_password": "yangi-parol-7"},
    )
    assert reset.status_code == 204
    login = await api.client.post(
        "/api/v1/auth/login", json={"username": "unutuvchan", "password": "yangi-parol-7"}
    )
    assert login.status_code == 200


async def test_password_guessing_is_throttled(api: Api) -> None:
    await api.register("nishon")
    statuses = [
        (
            await api.client.post(
                "/api/v1/auth/login", json={"username": "nishon", "password": f"taxmin-{i}"}
            )
        ).status_code
        for i in range(12)
    ]
    assert statuses[:10] == [422] * 10
    assert statuses[10:] == [429, 429]


async def test_telegram_bot_links_and_takes_proofs(api: Api) -> None:
    auth = await api.register()
    assert (await api.client.get("/api/v1/features")).json()["telegram_bot"] == "pit_test_bot"

    link = await api.client.post("/api/v1/me/telegram", headers=auth)
    url = link.json()["url"]
    assert url.startswith("https://t.me/pit_test_bot?start=")

    chat = {"id": 555, "type": "private"}

    async def webhook(message: dict[str, Any], secret: str = "hook-secret-0123456789") -> int:
        response = await api.client.post(
            "/api/v1/telegram/webhook",
            json={"update_id": 1, **message},
            headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        )
        return response.status_code

    start = {"message": {"chat": chat, "text": f"/start {url.split('start=')[1]}"}}
    assert await webhook(start, secret="guess") == 403  # only Telegram knows the secret
    assert await webhook(start) == 200
    welcome, ask_phone = api.telegram.to(555)[-2:]
    assert "Telegram ulandi" in welcome.text
    assert ask_phone.menu and ask_phone.menu[0][0] == ShareContact("📱 Raqamni yuborish")
    assert (await api.client.get("/api/v1/me", headers=auth)).json()["telegram_linked"]

    # Someone else's contact card is refused; the user's own number verifies the phone.
    other = {"phone_number": "998901112233", "user_id": 999}
    await webhook({"message": {"chat": chat, "from": {"id": 555}, "contact": other}})
    assert not (await api.client.get("/api/v1/me", headers=auth)).json()["phone_verified"]
    own = {"phone_number": "998901234567", "user_id": 555}
    await webhook({"message": {"chat": chat, "from": {"id": 555}, "contact": own}})
    me = (await api.client.get("/api/v1/me", headers=auth)).json()
    assert me["phone_verified"] and me["phone"] == "+998901234567"

    # Forgot password: the code arrives in Telegram, no SMS is spent.
    await api.client.post("/api/v1/auth/password/forgot", json={"username": "ali_2008"})
    code = re.search(r"\d{6}", api.telegram.last(555).text)
    assert code and not api.sms.sent
    reset = await api.client.post(
        "/api/v1/auth/password/reset",
        json={"username": "ali_2008", "code": code.group(), "new_password": "yangi-parol-7"},
    )
    assert reset.status_code == 204

    # Join on the website, prove from the chat: a real photo through the whole pipeline.
    reading = str(catalog_id("reading-30"))
    joined = await api.client.post(
        f"/api/v1/challenges/{reading}/join", json={"mode": "free"}, headers=auth
    )
    pid = joined.json()["id"]
    api.telegram.files["F1"] = jpeg()
    assert await webhook({"message": {"chat": chat, "photo": [{"file_id": "F1"}]}}) == 200
    assert "Qaysi vazifa" in api.telegram.last(555).text  # two tasks today: which one?
    press = {"id": "cb1", "data": f"p:{pid.replace('-', '')}:0", "message": {"chat": chat}}
    assert await webhook({"callback_query": press}) == 200
    await api.settle()

    detail = (await api.client.get(f"/api/v1/me/participations/{pid}", headers=auth)).json()
    read = next(t for t in detail["today"]["tasks"] if t["key"] == "read")
    assert read["proof_status"] == "approved"

    assert (await api.client.delete("/api/v1/me/telegram", headers=auth)).status_code == 204
    assert not (await api.client.get("/api/v1/me", headers=auth)).json()["telegram_linked"]


async def test_google_sign_up_then_sign_in(api: Api) -> None:
    api.google.accounts["cred-1"] = GoogleIdentity(sub="g-123", email="Ali.Valiyev@gmail.com")
    features = (await api.client.get("/api/v1/features")).json()
    assert features["google_client_id"] == "test-client.apps.googleusercontent.com"

    first = (await api.client.post("/api/v1/auth/google", json={"credential": "cred-1"})).json()
    assert first["access_token"] is None and first["suggested_username"] == "ali_valiyev"
    signup = {"Authorization": f"Bearer {first['signup_token']}"}
    assert (await api.client.get("/api/v1/me", headers=signup)).status_code == 401

    regions = (await api.client.get("/api/v1/regions")).json()
    created = await api.client.post(
        "/api/v1/auth/google/register",
        json={
            "signup_token": first["signup_token"],
            "username": first["suggested_username"],
            "birth_date": "2009-05-01",
            "region_id": regions[0]["id"],
            "accepted_terms_version": CURRENT_TERMS_VERSION,
        },
    )
    assert created.status_code == 201, created.text

    again = (await api.client.post("/api/v1/auth/google", json={"credential": "cred-1"})).json()
    assert again["user_id"] == created.json()["user_id"] and again["access_token"]
    me = await api.client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {again['access_token']}"}
    )
    assert me.json()["username"] == "ali_valiyev"

    # No password was ever set, so password login is impossible for this account.
    login = await api.client.post(
        "/api/v1/auth/login", json={"username": "ali_valiyev", "password": "anything-1"}
    )
    assert login.status_code == 422
    forged = await api.client.post("/api/v1/auth/google", json={"credential": "forged"})
    assert forged.status_code == 422


async def test_together_invite_join_and_group_board(api: Api) -> None:
    owner = await api.register("ali_2008")
    friend = await api.register("vali_2009")
    running = str(catalog_id("reading-30"))
    pid = (
        await api.client.post(
            f"/api/v1/challenges/{running}/join", json={"mode": "free"}, headers=owner
        )
    ).json()["id"]
    assert (
        await api.client.get(f"/api/v1/me/participations/{pid}/group", headers=owner)
    ).json() is None

    code = (await api.client.post(f"/api/v1/me/participations/{pid}/group", headers=owner)).json()[
        "invite_code"
    ]
    preview = await api.client.get(f"/api/v1/groups/{code}")  # no account needed to look
    assert preview.status_code == 200
    assert preview.json()["owner"] == "ali_2008" and preview.json()["members"] == 1

    joined = await api.client.post(f"/api/v1/groups/{code}/join", headers=friend)
    assert joined.status_code == 201, joined.text

    board = (await api.client.get(f"/api/v1/me/participations/{pid}/group", headers=owner)).json()
    assert [m["username"] for m in board["members"]] == ["ali_2008", "vali_2009"]
    assert board["members"][0]["is_me"] and board["members"][0]["is_owner"]
    notes = (await api.client.get("/api/v1/me/notifications", headers=owner)).json()
    assert any("vali_2009" in n["body"] for n in notes)


async def test_export_then_erase_the_account(api: Api) -> None:
    auth = await api.register("ali_2008")
    reading = str(catalog_id("reading-30"))
    await api.client.post(f"/api/v1/challenges/{reading}/join", json={"mode": "free"}, headers=auth)

    export = await api.client.get("/api/v1/me/export", headers=auth)
    assert export.status_code == 200
    assert "attachment" in export.headers["content-disposition"]
    data = export.json()
    assert data["profile"]["username"] == "ali_2008"
    assert data["challenges"][0]["status"] == "active"
    assert data["notifications"]  # the coach's welcome message

    wrong = await api.client.request(
        "DELETE", "/api/v1/me", json={"username": "boshqa"}, headers=auth
    )
    assert wrong.status_code == 422
    erased = await api.client.request(
        "DELETE", "/api/v1/me", json={"username": "ali_2008"}, headers=auth
    )
    assert erased.status_code == 204

    assert (await api.client.get("/api/v1/me", headers=auth)).status_code == 401  # old token
    login = await api.client.post(
        "/api/v1/auth/login", json={"username": "ali_2008", "password": "kuchli-parol-1"}
    )
    assert login.status_code == 422
    # The username is free again for someone new.
    assert await api.register("ali_2008")


async def test_report_reaches_the_moderator_queue(api: Api) -> None:
    reporter = await api.register("ali_2008")
    await api.register("yomon_nom")
    filed = await api.client.post(
        "/api/v1/reports",
        json={"username": "yomon_nom", "reason": "bad_name", "details": "Haqoratli username"},
        headers=reporter,
    )
    assert filed.status_code == 201, filed.text

    moderator = await api.register("moder_1")
    assert (await api.client.get("/api/v1/admin/reports", headers=moderator)).status_code == 403
    await make_moderator(api.container, "moder_1")
    queue = (await api.client.get("/api/v1/admin/reports", headers=moderator)).json()
    assert [(r["reported"], r["reason"], r["reports_against"]) for r in queue] == [
        ("yomon_nom", "bad_name", 1)
    ]

    resolved = await api.client.post(
        f"/api/v1/admin/reports/{queue[0]['id']}/resolve",
        json={"action": "reset_username"},
        headers=moderator,
    )
    assert resolved.status_code == 204
    assert (await api.client.get("/api/v1/admin/reports", headers=moderator)).json() == []


async def test_a_proof_whose_check_was_lost_is_checked_again(api: Api) -> None:
    auth = await api.register()
    reading = str(catalog_id("reading-30"))
    pid = (
        await api.client.post(
            f"/api/v1/challenges/{reading}/join", json={"mode": "free"}, headers=auth
        )
    ).json()["id"]
    proof = await api.client.post(
        "/api/v1/proofs",
        data={"participation_id": pid, "task_key": "read"},
        files={"file": ("page.jpg", jpeg(), "image/jpeg")},
        headers=auth,
    )
    await api.settle()
    proof_id = proof.json()["id"]
    # Simulate a restart that killed the check: pending, and submitted a while ago.
    async with api.container.engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE proofs SET status = 'pending', ai_decision = NULL, "
                "submitted_at = now() - interval '10 minutes' WHERE id = :id"
            ),
            {"id": proof_id},
        )
    assert await requeue_stale_proofs(api.container) == 1
    await api.settle()
    status = (await api.client.get(f"/api/v1/proofs/{proof_id}", headers=auth)).json()
    assert status["status"] == "approved"


async def test_analytics_for_moderators(api: Api) -> None:
    auth = await api.register("ali_2008")
    reading = str(catalog_id("reading-30"))
    pid = (
        await api.client.post(
            f"/api/v1/challenges/{reading}/join", json={"mode": "free"}, headers=auth
        )
    ).json()["id"]
    await api.client.post(
        "/api/v1/proofs",
        data={"participation_id": pid, "task_key": "read"},
        files={"file": ("page.jpg", jpeg(), "image/jpeg")},
        headers=auth,
    )
    await api.settle()
    assert (await api.client.get("/api/v1/admin/analytics", headers=auth)).status_code == 403

    await make_moderator(api.container, "ali_2008")
    data = (await api.client.get("/api/v1/admin/analytics", headers=auth)).json()
    assert (data["users"], data["dau"], data["proofs_30d"]) == (1, 1, 1)
    assert [step["count"] for step in data["funnel"]] == [1, 1, 1, 1, 0]
    assert len(data["daily"]) == 30 and data["daily"][-1]["active"] == 1
