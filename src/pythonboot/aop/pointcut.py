"""Pointcuts based on qualified method names, annotations, or predicates."""

from dataclasses import dataclass
from fnmatch import fnmatchcase
import inspect
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class MethodInfo:
    bean_name: str
    target_type: type
    method_name: str
    method: Callable[..., Any]

    @property
    def qualified_name(self) -> str:
        return f"{self.target_type.__module__}.{self.target_type.__qualname__}.{self.method_name}"


@dataclass(frozen=True)
class MethodAnnotation:
    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Aspect annotation names must be non-empty strings")

    def __call__(self, method: F) -> F:
        """Mark a business method without changing its signature or coroutine type."""
        if not inspect.isfunction(method):
            raise TypeError("Aspect annotations can only decorate instance methods")
        names = frozenset(getattr(method, "__pythonboot_annotations__", ()))
        method.__pythonboot_annotations__ = names | {self.name}
        return method

    def matches(self, method: MethodInfo) -> bool:
        return self.name in getattr(method.method, "__pythonboot_annotations__", ())


def annotation(name: str) -> MethodAnnotation:
    """Create an aspect annotation usable as @logged and @around(logged)."""
    return MethodAnnotation(name)


def _matches(pattern: tuple[str, ...], name: tuple[str, ...]) -> bool:
    if not pattern:
        return not name
    if pattern[0] == "**":
        return _matches(pattern[1:], name) or (
            bool(name) and _matches(pattern, name[1:])
        )
    return bool(name) and fnmatchcase(name[0], pattern[0]) and _matches(pattern[1:], name[1:])


@dataclass(frozen=True)
class Pointcut:
    expression: str | MethodAnnotation | Callable[[MethodInfo], bool]

    def __post_init__(self) -> None:
        if isinstance(self.expression, str):
            if not self.expression or any(
                not part or ("**" in part and part != "**")
                for part in self.expression.split(".")
            ):
                raise ValueError("Pointcut expressions must not be empty; ** must occupy an entire segment")
        elif not callable(self.expression):
            raise TypeError("Pointcuts must be method path expressions, annotations, or matching functions")

    def matches(self, method: MethodInfo) -> bool:
        if isinstance(self.expression, MethodAnnotation):
            return self.expression.matches(method)
        if callable(self.expression):
            return bool(self.expression(method))
        return _matches(tuple(self.expression.split(".")), tuple(method.qualified_name.split(".")))


def pointcut(expression: str | MethodAnnotation | Callable[[MethodInfo], bool]) -> Pointcut:
    return Pointcut(expression)
