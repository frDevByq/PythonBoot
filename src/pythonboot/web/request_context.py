"""Access the HTTP request bound to the current execution context."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from threading import RLock
from typing import Any

from fastapi import Request
from starlette.types import Message

_current_request: ContextVar[Request | None] = ContextVar(
    "pythonboot_current_request", default=None,
)


@dataclass
class _RequestData:
    values: dict[str, Any] = field(default_factory=dict)
    lock: Any = field(default_factory=RLock)


_current_data: ContextVar[_RequestData | None] = ContextVar(
    "pythonboot_request_data", default=None,
)
_current_response: ContextVar["ResponseContext | None"] = ContextVar(
    "pythonboot_current_response", default=None,
)


class ResponseContext:
    """Mutable response settings applied before the ASGI response starts."""

    def __init__(self) -> None:
        self._status_code: int | None = None
        self._headers: dict[bytes, bytes] = {}
        self._cookies: list[bytes] = []
        self._committed = False
        self._lock = RLock()

    @property
    def status_code(self) -> int | None:
        return self._status_code

    @status_code.setter
    def status_code(self, value: int) -> None:
        if not isinstance(value, int) or not 100 <= value <= 599:
            raise ValueError("status_code must be an integer between 100 and 599")
        with self._lock:
            self._ensure_mutable()
            self._status_code = value

    def set_header(self, name: str, value: str) -> None:
        """Set a response header."""
        if not isinstance(name, str) or not isinstance(value, str):
            raise TypeError("response header name and value must be strings")
        with self._lock:
            self._ensure_mutable()
            self._headers[name.encode("latin-1").lower()] = value.encode("latin-1")

    def set_cookie(self, key: str, value: str, **options: Any) -> None:
        """Add a Set-Cookie header."""
        cookie = SimpleCookie()
        cookie[key] = value
        for name, option_value in options.items():
            cookie[key][name.replace("_", "-")] = option_value
        with self._lock:
            self._ensure_mutable()
            self._cookies.append(cookie.output(header="").strip().encode("latin-1"))

    def redirect(self, url: str, status_code: int = 307) -> None:
        """Set a redirect location and status code."""
        self.status_code = status_code
        self.set_header("Location", url)

    def apply(self, message: Message) -> Message:
        """Apply pending settings to an ASGI response-start message."""
        with self._lock:
            self._committed = True
            headers = [
                (name, value) for name, value in message.get("headers", [])
                if name.lower() not in self._headers
            ]
            headers.extend(self._headers.items())
            headers.extend((b"set-cookie", cookie) for cookie in self._cookies)
            return {
                **message,
                "status": self._status_code if self._status_code is not None else message["status"],
                "headers": headers,
            }

    def _ensure_mutable(self) -> None:
        if self._committed:
            raise RuntimeError("The HTTP response has already started")


class RequestContextHolder:
    """Expose the current request to controllers, services, and advice."""

    @staticmethod
    def get_request() -> Request:
        request = _current_request.get()
        if request is None:
            raise RuntimeError("No HTTP request is bound to the current execution context")
        return request

    @staticmethod
    def get_response() -> ResponseContext:
        """Return the mutable response context for the current request."""
        response = _current_response.get()
        if response is None:
            raise RuntimeError("No HTTP request is bound to the current execution context")
        return response

    @staticmethod
    def putData(key: str, value: Any) -> None:
        """Store a custom value in the current request's thread-safe map."""
        data = RequestContextHolder._data()
        with data.lock:
            data.values[key] = value

    @staticmethod
    def getData(key: str, default: Any = None) -> Any:
        """Read a custom value from the current request's thread-safe map."""
        data = RequestContextHolder._data()
        with data.lock:
            return data.values.get(key, default)

    @staticmethod
    def _data() -> _RequestData:
        data = _current_data.get()
        if data is None:
            raise RuntimeError("No HTTP request is bound to the current execution context")
        return data

    @staticmethod
    @contextmanager
    def use(request: Request, response: ResponseContext) -> Iterator[Request]:
        """Bind a request temporarily and restore the previous binding on exit."""
        token = _current_request.set(request)
        data_token = _current_data.set(_RequestData())
        response_token = _current_response.set(response)
        try:
            yield request
        finally:
            _current_response.reset(response_token)
            _current_data.reset(data_token)
            _current_request.reset(token)
