"""FastAPI routing, dependency injection, and exception handling integration."""

from pythonboot.web.integration import inject, register_routers
from pythonboot.web.context_middleware import ApplicationContextMiddleware
from pythonboot.web.decorators import controller, delete, get, patch, post, put, route

__all__ = [
    "controller", "route", "get", "post", "put", "patch", "delete",
    "inject", "register_routers",
    "ApplicationContextMiddleware",
]
