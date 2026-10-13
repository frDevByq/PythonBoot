"""Aspect and advice declarations without decoration-time instantiation."""

import inspect
from dataclasses import dataclass
from typing import Any, Callable, Literal, TypeVar

from pythonboot.aop.pointcut import MethodAnnotation, MethodInfo, Pointcut
from pythonboot.beans import Scope, component

T = TypeVar("T", bound=type)
F = TypeVar("F", bound=Callable[..., Any])
AdviceKind = Literal["before", "after", "after_returning", "after_throwing", "around"]
Cut = str | Pointcut | MethodAnnotation | Callable[[MethodInfo], bool]


@dataclass(frozen=True)
class AdviceDefinition:
    kind: AdviceKind
    pointcut: Pointcut
    order: int


def aspect(
    cls: T | None = None, *, order: int = 0, name: str | None = None,
    init_method: str | None = None, destroy_method: str | None = None,
    lazy: bool = False,
    scope: Scope = "singleton", primary: bool = False,
    qualifiers: tuple[str, ...] = (), depends_on: tuple[str, ...] = (),
) -> T | Callable[[T], T]:
    """Declare a managed aspect; lower order values enter the advice chain first."""
    def decorate(target: T) -> T:
        if not inspect.isclass(target):
            raise TypeError("@aspect can only decorate classes")
        component(
            target, name=name, init_method=init_method, destroy_method=destroy_method,
            lazy=lazy, scope=scope, primary=primary, qualifiers=qualifiers, depends_on=depends_on,
        )
        target.__pythonboot_aspect__ = order
        return target

    return decorate(cls) if cls is not None else decorate


def _advice(kind: AdviceKind, cut: Cut, order: int) -> Callable[[F], F]:
    matcher = cut if isinstance(cut, Pointcut) else Pointcut(cut)

    def decorate(method: F) -> F:
        if not inspect.isfunction(method):
            raise TypeError("Advice must be declared as an aspect instance method")
        definitions = list(getattr(method, "__pythonboot_advices__", ()))
        definitions.append(AdviceDefinition(kind, matcher, order))
        method.__pythonboot_advices__ = tuple(definitions)
        return method

    return decorate


def before(cut: Cut, *, order: int = 0) -> Callable[[F], F]:
    return _advice("before", cut, order)


def after(cut: Cut, *, order: int = 0) -> Callable[[F], F]:
    return _advice("after", cut, order)


def after_returning(cut: Cut, *, order: int = 0) -> Callable[[F], F]:
    return _advice("after_returning", cut, order)


def after_throwing(cut: Cut, *, order: int = 0) -> Callable[[F], F]:
    return _advice("after_throwing", cut, order)


def around(cut: Cut, *, order: int = 0) -> Callable[[F], F]:
    return _advice("around", cut, order)
