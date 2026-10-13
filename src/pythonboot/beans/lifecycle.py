"""Bean initialization callback declarations."""

import inspect
from typing import Any, Callable, TypeVar

from pythonboot.exceptions import BeanDefinitionError

F = TypeVar("F", bound=Callable[..., Any])


def postconstruct(method: F | None = None) -> F | Callable[[F], F]:
    """Invoke an instance method once after dependency injection completes."""
    def decorate(target: F) -> F:
        if not inspect.isfunction(target):
            raise TypeError("@postconstruct can only decorate instance methods")
        parameters = tuple(inspect.signature(target).parameters.values())
        if (
            len(parameters) != 1 or parameters[0].name != "self"
            or parameters[0].kind not in (
                inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ):
            raise TypeError("@postconstruct methods must accept only self")
        if inspect.isgeneratorfunction(target) or inspect.isasyncgenfunction(target):
            raise TypeError("@postconstruct does not support generator methods")
        target.__pythonboot_postconstruct__ = True
        return target

    return decorate(method) if method is not None else decorate


def ondestroy(method: F | None = None) -> F | Callable[[F], F]:
    """Invoke an instance method once before a singleton bean is destroyed."""
    def decorate(target: F) -> F:
        if not inspect.isfunction(target):
            raise TypeError("@ondestroy can only decorate instance methods")
        parameters = tuple(inspect.signature(target).parameters.values())
        if (
            len(parameters) != 1 or parameters[0].name != "self"
            or parameters[0].kind not in (
                inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ):
            raise TypeError("@ondestroy methods must accept only self")
        if inspect.isgeneratorfunction(target) or inspect.isasyncgenfunction(target):
            raise TypeError("@ondestroy does not support generator methods")
        target.__pythonboot_ondestroy__ = True
        return target

    return decorate(method) if method is not None else decorate


def get_postconstruct_methods(bean_type: type) -> tuple[str, ...]:
    """Discover callbacks from base to derived classes, respecting method resolution."""
    methods: list[str] = []
    for cls in reversed(bean_type.__mro__):
        for name, descriptor in vars(cls).items():
            method = descriptor.__func__ if isinstance(descriptor, (staticmethod, classmethod)) else descriptor
            if not getattr(method, "__pythonboot_postconstruct__", False):
                continue
            if inspect.getattr_static(bean_type, name) is not descriptor:
                continue
            if isinstance(descriptor, (staticmethod, classmethod)):
                raise BeanDefinitionError(f"@postconstruct does not support static or class methods: {bean_type.__name__}.{name}")
            methods.append(name)
    return tuple(methods)


def get_ondestroy_methods(bean_type: type) -> tuple[str, ...]:
    """Discover callbacks from derived to base classes, respecting method resolution."""
    methods: list[str] = []
    for cls in bean_type.__mro__:
        for name, descriptor in vars(cls).items():
            method = descriptor.__func__ if isinstance(descriptor, (staticmethod, classmethod)) else descriptor
            if not getattr(method, "__pythonboot_ondestroy__", False):
                continue
            if inspect.getattr_static(bean_type, name) is not descriptor:
                continue
            if isinstance(descriptor, (staticmethod, classmethod)):
                raise BeanDefinitionError(f"@ondestroy does not support static or class methods: {bean_type.__name__}.{name}")
            methods.append(name)
    return tuple(methods)
