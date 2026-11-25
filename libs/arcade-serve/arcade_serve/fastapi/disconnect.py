import asyncio

from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CancelOnDisconnectMiddleware:
    """Cancels a worker request whose caller hangs up before it is answered.

    The Engine stops waiting for a tool call at its own per-call timeout and
    closes the connection; nothing the tool does after that reaches anyone.
    Cancelling the request stops the tool at its next await. Starlette's function
    middlewares never pass the disconnect on to the route, so this has to sit
    outside them, on the raw ASGI channel.

    The body reaches the app as it arrives, so a request refused before its body
    is read (an unauthenticated one) is never buffered. Listening for the hang-up
    starts once the app has read the whole body: until then the channel is the
    app's.
    """

    def __init__(self, app: ASGIApp, path_prefix: str = "/worker") -> None:
        self.app = app
        self.path_prefix = path_prefix.rstrip("/")

    def _applies(self, scope: Scope) -> bool:
        if scope["type"] != "http":
            return False
        path: str = scope["path"]
        root_path: str = scope.get("root_path", "")
        if root_path and path.startswith(root_path):
            path = path[len(root_path) :]
        return path == self.path_prefix or path.startswith(self.path_prefix + "/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self._applies(scope):
            await self.app(scope, receive, send)
            return
        body_read = asyncio.Event()
        hung_up = asyncio.Event()
        answered = asyncio.Event()

        async def app_receive() -> Message:
            if body_read.is_set():
                await hung_up.wait()
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] != "http.request" or not message.get("more_body"):
                body_read.set()
            return message

        async def send_tracking(message: Message) -> None:
            if message["type"] == "http.response.body" and not message.get("more_body"):
                answered.set()
            await send(message)

        call = asyncio.ensure_future(self.app(scope, app_receive, send_tracking))
        watcher = asyncio.ensure_future(
            _cancel_on_hang_up(receive, call, body_read, answered, hung_up)
        )
        try:
            await call
        except asyncio.CancelledError:
            # Swallowed only when the hang-up is the sole reason: a cancel of this
            # request itself (server shutdown) still propagates. Python 3.10 cannot
            # tell the two apart when they coincide, and the hang-up wins there.
            if not hung_up.is_set() or _cancelling():
                raise
        finally:
            watcher.cancel()


def _cancelling() -> bool:
    current = asyncio.current_task()
    cancelling = getattr(current, "cancelling", None)  # Python 3.11+
    return bool(cancelling and cancelling())


async def _cancel_on_hang_up(
    receive: Receive,
    call: asyncio.Future,
    body_read: asyncio.Event,
    answered: asyncio.Event,
    hung_up: asyncio.Event,
) -> None:
    await body_read.wait()
    while (await receive())["type"] != "http.disconnect":
        pass
    # A server answers receive() with a disconnect once the response is complete,
    # while work after it (a background task) may still be running.
    if answered.is_set():
        return
    hung_up.set()
    call.cancel()
