"""FastAPI routing, dependency injection, and exception handling integration."""

from pythonboot.web.integration import inject, register_exception_handlers, register_routers
from pythonboot.web.context_middleware import ApplicationContextMiddleware
from pythonboot.web.decorators import (
    controller, controller_advise, delete, exception_handler, get, patch, post, put, route,
)

__all__ = [
    "controller", "controller_advise", "exception_handler", "route", "get", "post", "put", "patch", "delete",
    "inject", "register_routers", "register_exception_handlers",
    "ApplicationContextMiddleware",
]
