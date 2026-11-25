import asyncio

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CancelOnDisconnectMiddleware:
    """Cancels a worker request whose caller hangs up before it is answered.

    The Engine stops waiting for a tool call at its own per-call timeout and
    closes the connection; nothing the tool does after that reaches anyone.
    Cancelling the request stops the tool at its next await. Starlette's function
    middlewares never pass the disconnect on to the route, so this has to sit
    outside them, on the raw ASGI channel.
    """

    def __init__(self, app: ASGIApp, path_prefix: str = "/worker") -> None:
        self.app = app
        self.path_prefix = path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(self.path_prefix):
            await self.app(scope, receive, send)
            return
        body = await _read_body(receive)
        if body is None:
            return
        hung_up = asyncio.Event()
        answered = asyncio.Event()

        async def replay() -> Message:
            if body:
                return body.pop(0)
            await hung_up.wait()
            return {"type": "http.disconnect"}

        async def send_tracking(message: Message) -> None:
            if message["type"] == "http.response.body" and not message.get("more_body"):
                answered.set()
            await send(message)

        call = asyncio.ensure_future(self.app(scope, replay, send_tracking))
        watcher = asyncio.ensure_future(_cancel_on_hang_up(receive, call, answered, hung_up))
        try:
            await call
        except asyncio.CancelledError:
            # Swallowed only when the hang-up is the sole reason: a cancel of this
            # request itself (server shutdown) still propagates.
            if not hung_up.is_set() or _cancelling():
                raise
        finally:
            watcher.cancel()


def _cancelling() -> bool:
    current = asyncio.current_task()
    cancelling = getattr(current, "cancelling", None)  # Python 3.11+
    return bool(cancelling and cancelling())


async def _read_body(receive: Receive) -> list[Message] | None:
    """Every request message up to the end of the body, or None when the caller
    hangs up first."""
    body: list[Message] = []
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            return None
        body.append(message)
        if not message.get("more_body"):
            return body


async def _cancel_on_hang_up(
    receive: Receive, call: asyncio.Future, answered: asyncio.Event, hung_up: asyncio.Event
) -> None:
    while (await receive())["type"] != "http.disconnect":
        pass
    if answered.is_set():
        return
    hung_up.set()
    call.cancel()
