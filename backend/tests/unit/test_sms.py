import httpx

from pit.modules.identity.infrastructure.security import EskizSmsSender


def eskiz(handler: httpx.MockTransport) -> EskizSmsSender:
    return EskizSmsSender(
        email="owner@example.uz",
        password="secret",
        sender="4546",
        client=httpx.AsyncClient(transport=handler),
    )


async def test_logs_in_once_and_sends_without_plus_sign() -> None:
    calls: list[tuple[str, dict[str, str]]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        form = dict(httpx.QueryParams(request.content.decode()))
        calls.append((request.url.path, form))
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"data": {"token": "t1"}})
        assert request.headers["Authorization"] == "Bearer t1"
        return httpx.Response(200, json={"status": "waiting"})

    sender = eskiz(httpx.MockTransport(handle))
    await sender.send("+998901234567", "kod: 123456")
    await sender.send("+998901234567", "kod: 654321")

    paths = [path for path, _ in calls]
    assert paths.count("/api/auth/login") == 1  # token is cached
    assert calls[-1][1]["mobile_phone"] == "998901234567"
    assert calls[-1][1]["from"] == "4546"


async def test_revoked_token_is_renewed_once() -> None:
    tokens = iter(["old", "new"])
    sent_with: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/auth/login"):
            return httpx.Response(200, json={"data": {"token": next(tokens)}})
        sent_with.append(request.headers["Authorization"])
        ok = request.headers["Authorization"] == "Bearer new"
        return httpx.Response(200 if ok else 401, json={})

    await eskiz(httpx.MockTransport(handle)).send("+998901234567", "salom")
    assert sent_with == ["Bearer old", "Bearer new"]
