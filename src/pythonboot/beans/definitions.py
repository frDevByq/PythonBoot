"""Component declarations and scanning metadata."""

from dataclasses import dataclass
import inspect
from typing import Any, Callable, Literal, TypeVar

T = TypeVar("T", bound=type)
F = TypeVar("F", bound=Callable[..., Any])
Scope = Literal["singleton", "prototype"]


@dataclass(frozen=True)
class ComponentOptions:
    name: str | None = None
    init_method: str | None = None
    destroy_method: str | None = None
    lazy: bool = False
    scope: Scope = "singleton"
    primary: bool = False
    qualifiers: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.scope not in ("singleton", "prototype"):
            raise ValueError("scope must be singleton or prototype")
        for label, value in (("name", self.name), ("init_method", self.init_method), ("destroy_method", self.destroy_method)):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{label} must be a non-empty string")
        for label in ("qualifiers", "depends_on"):
            values = getattr(self, label)
            if isinstance(values, str) or any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{label} must be a sequence of non-empty strings")
            object.__setattr__(self, label, tuple(dict.fromkeys(values)))


@dataclass(frozen=True)
class BeanDefinition:
    name: str
    bean_type: type
    factory: Callable[..., Any]
    owner: type | None = None
    init_method: str | None = None
    destroy_method: str | None = None
    lazy: bool = False
    scope: Scope = "singleton"
    primary: bool = False
    qualifiers: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        options = ComponentOptions(
            self.name, self.init_method, self.destroy_method, self.lazy,
            self.scope, self.primary, self.qualifiers, self.depends_on,
        )
        object.__setattr__(self, "qualifiers", options.qualifiers)
        object.__setattr__(self, "depends_on", options.depends_on)


def component(
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
    """Declare a managed component, singleton by default, without instantiating it."""
    def decorate(target: T) -> T:
        if not inspect.isclass(target):
            raise TypeError("Component decorators can only decorate classes")
        target.__pythonboot_component__ = ComponentOptions(
            name, init_method, destroy_method, lazy, scope, primary, qualifiers, depends_on
        )
        return target

    return decorate(cls) if cls is not None else decorate


service = component
configuration = component


def bean(
    factory: F | None = None,
    *,
    name: str | None = None,
    init_method: str | None = None,
    destroy_method: str | None = None,
    lazy: bool = False,
    scope: Scope = "singleton",
    primary: bool = False,
    qualifiers: tuple[str, ...] = (),
    depends_on: tuple[str, ...] = (),
) -> F | Callable[[F], F]:
    """Declare a module-level factory or a configuration bean factory method."""
    def decorate(target: F) -> F:
        if not inspect.isfunction(target):
            raise TypeError("@bean decorates factory methods; use @component for classes")
        target.__pythonboot_bean__ = ComponentOptions(
            name, init_method, destroy_method, lazy, scope, primary, qualifiers, depends_on
        )
        return target

    return decorate(factory) if factory is not None else decorate
