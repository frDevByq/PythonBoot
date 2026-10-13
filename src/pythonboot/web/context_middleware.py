"""Bind the application container for HTTP, WebSocket, and background callbacks."""

from fastapi import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from pythonboot.context import ApplicationContext
from pythonboot.util import ContextUtil
from pythonboot.web.request_context import RequestContextHolder, ResponseContext


class ApplicationContextMiddleware:
    def __init__(self, app: ASGIApp, context: ApplicationContext) -> None:
        self.app = app
        self.context = context

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        with ContextUtil.use(self.context):
            if scope["type"] != "http":
                await self.app(scope, receive, send)
                return
            body_parts: list[bytes] = []

            async def request_receive() -> Message:
                message = await receive()
                if message["type"] == "http.request":
                    body_parts.append(message.get("body", b""))
                    if not message.get("more_body", False):
                        request._body = b"".join(body_parts)
                        body_parts.clear()
                return message

            request = Request(scope, receive=request_receive)
            response = ResponseContext()

            async def response_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    await send(response.apply(message))
                    return
                await send(message)

            with RequestContextHolder.use(request, response):
                await self.app(scope, request_receive, response_send)
