"""Bind the application container for HTTP, WebSocket, and background callbacks."""

from starlette.types import ASGIApp, Receive, Scope, Send

from pythonboot.context import ApplicationContext
from pythonboot.util import ContextUtil


class ApplicationContextMiddleware:
    def __init__(self, app: ASGIApp, context: ApplicationContext) -> None:
        self.app = app
        self.context = context

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        with ContextUtil.use(self.context):
            await self.app(scope, receive, send)
