"""Class-based controllers and method route declarations."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from pythonboot.beans import Scope, component

T = TypeVar("T", bound=type)
F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class RouteDefinition:
    path: str
    methods: tuple[str, ...]
    options: dict[str, Any]


def controller(
    cls: T | None = None,
    *,
    prefix: str = "",
    tags: list[str] | None = None,
    name: str | None = None,
    init_method: str | None = None,
    destroy_method: str | None = None,
    lazy: bool = False,
    scope: Scope = "singleton",
    primary: bool = False,
    qualifiers: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
    **router_options: Any,
) -> T | Callable[[T], T]:
    """Declare a controller, singleton by default, with container-injected dependencies."""
    def decorate(target: T) -> T:
        if not inspect.isclass(target):
            raise TypeError("@controller can only decorate classes")
        component(
            target, name=name, init_method=init_method, destroy_method=destroy_method,
            lazy=lazy, scope=scope, primary=primary, qualifiers=qualifiers, depends_on=depends_on,
        )
        target.__pythonboot_controller__ = {
            **router_options, "prefix": prefix, "tags": list(tags or []),
        }
        return target

    return decorate(cls) if cls is not None else decorate


def controller_advise(
    cls: T | None = None,
    *,
    name: str | None = None,
    init_method: str | None = None,
    destroy_method: str | None = None,
    lazy: bool = False,
    scope: Scope = "singleton",
    primary: bool = False,
    qualifiers: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
) -> T | Callable[[T], T]:
    """Declare a managed global exception handler component."""
    def decorate(target: T) -> T:
        if not inspect.isclass(target):
            raise TypeError("@controller_advise can only decorate classes")
        component(
            target, name=name, init_method=init_method, destroy_method=destroy_method,
            lazy=lazy, scope=scope, primary=primary, qualifiers=qualifiers, depends_on=depends_on,
        )
        target.__pythonboot_controller_advise__ = True
        return target

    return decorate(cls) if cls is not None else decorate


def exception_handler(
    exception_type: int | type[Exception],
) -> Callable[[F], F]:
    """Map a controller advice instance method to an exception or status code."""
    if not isinstance(exception_type, int) and (
        not inspect.isclass(exception_type) or not issubclass(exception_type, Exception)
    ):
        raise TypeError("exception_handler target must be an exception type or status code")

    def decorate(method: F) -> F:
        if not inspect.isfunction(method):
            raise TypeError("@exception_handler can only decorate instance methods")
        handlers = list(getattr(method, "__pythonboot_exception_handlers__", ()))
        handlers.append(exception_type)
        method.__pythonboot_exception_handlers__ = tuple(handlers)
        return method

    return decorate


def route(
    path: str, *, methods: tuple[str, ...] = ("GET",), **options: Any
) -> Callable[[F], F]:
    """Declare a controller instance route using FastAPI add_api_route options."""
    def decorate(method: F) -> F:
        if not inspect.isfunction(method):
            raise TypeError("Route decorators can only decorate controller instance methods")
        definitions = list(getattr(method, "__pythonboot_routes__", ()))
        definitions.append(RouteDefinition(path, tuple(methods), dict(options)))
        method.__pythonboot_routes__ = tuple(definitions)
        return method

    return decorate


def get(path: str, **options: Any) -> Callable[[F], F]:
    return route(path, methods=("GET",), **options)


def post(path: str, **options: Any) -> Callable[[F], F]:
    return route(path, methods=("POST",), **options)


def put(path: str, **options: Any) -> Callable[[F], F]:
    return route(path, methods=("PUT",), **options)


def patch(path: str, **options: Any) -> Callable[[F], F]:
    return route(path, methods=("PATCH",), **options)


def delete(path: str, **options: Any) -> Callable[[F], F]:
    return route(path, methods=("DELETE",), **options)
