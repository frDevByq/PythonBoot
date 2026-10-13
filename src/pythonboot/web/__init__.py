"""FastAPI routing, dependency injection, and exception handling integration."""

from pythonboot.web.integration import inject, register_exception_handlers, register_routers
from pythonboot.web.docs import register_api_docs, resolve_docs_options
from pythonboot.web.datetime import DateTimeFormatMiddleware, date_time, resolve_datetime_format
from pythonboot.web.context_middleware import ApplicationContextMiddleware
from pythonboot.web.request_context import RequestContextHolder
from pythonboot.web.decorators import (
    controller, controller_advise, delete, exception_handler, get, patch, post, put, route,
)

__all__ = [
    "controller", "controller_advise", "exception_handler", "route", "get", "post", "put", "patch", "delete",
    "inject", "register_routers", "register_exception_handlers", "resolve_datetime_format",
    "DateTimeFormatMiddleware", "date_time",
    "resolve_docs_options", "register_api_docs",
    "ApplicationContextMiddleware",
    "RequestContextHolder",
]
