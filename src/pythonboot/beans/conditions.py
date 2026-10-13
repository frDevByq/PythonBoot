"""Declarative conditions evaluated while assembling auto-configurations."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Any, TypeVar

from pythonboot.beans.definitions import BeanDefinition

T = TypeVar("T")
_MISSING = object()


@dataclass(frozen=True)
class Condition:
    kind: str
    values: tuple[type | str, ...] = ()
    having_value: Any = _MISSING
    match_if_missing: bool = False

    def matches(
        self, definitions: tuple[BeanDefinition, ...], configuration: Mapping[str, Any],
    ) -> bool:
        if self.kind == "module":
            for module in self.values:
                try:
                    if find_spec(module) is None:
                        return False
                except ModuleNotFoundError as error:
                    if error.name == module or module.startswith(f"{error.name}."):
                        return False
                    raise
            return True
        if self.kind == "property":
            value: Any = configuration
            for part in self.values[0].split("."):
                if not isinstance(value, Mapping) or part not in value:
                    return self.match_if_missing
                value = value[part]
            if self.having_value is _MISSING:
                return value is not None and str(value).lower() != "false"
            return str(value).lower() == str(self.having_value).lower()
        matches = tuple(
            any(
                definition.name == value if isinstance(value, str)
                else issubclass(definition.bean_type, value)
                for definition in definitions
            )
            for value in self.values
        )
        return not any(matches) if self.kind == "missing_bean" else all(matches)


def _declare(condition: Condition) -> Callable[[T], T]:
    def decorate(target: T) -> T:
        if not isinstance(target, type) and not callable(target):
            raise TypeError("Conditions can only decorate configuration classes or bean factories")
        conditions = vars(target).get("__pythonboot_conditions__", ())
        target.__pythonboot_conditions__ = (*conditions, condition)
        return target
    return decorate


def conditional_on_module(*modules: str) -> Callable[[T], T]:
    """Enable an auto-configuration or factory when all modules are available."""
    if not modules or any(
        not isinstance(module, str) or not all(part.isidentifier() for part in module.split("."))
        for module in modules
    ):
        raise ValueError("Module conditions require non-empty dotted module names")
    return _declare(Condition("module", modules))


def conditional_on_property(
    name: str, *, having_value: Any = _MISSING, match_if_missing: bool = False,
) -> Callable[[T], T]:
    """Match a dotted application YAML property without creating any beans."""
    if not isinstance(name, str) or any(not part.strip() for part in name.split(".")):
        raise ValueError("Property conditions require a non-empty dotted name")
    return _declare(Condition("property", (name,), having_value, match_if_missing))


def _bean_condition(kind: str, beans: tuple[type | str, ...]) -> Callable[[T], T]:
    if not beans or any(
        not isinstance(bean, (type, str)) or isinstance(bean, str) and not bean.strip()
        for bean in beans
    ):
        raise ValueError("Bean conditions require bean types or non-empty bean names")
    return _declare(Condition(kind, beans))


def conditional_on_bean(*beans: type | str) -> Callable[[T], T]:
    """Match when all specified bean types or names have been registered."""
    return _bean_condition("bean", beans)


def conditional_on_missing_bean(*beans: type | str) -> Callable[[T], T]:
    """Back off when any specified bean type or name is already registered."""
    return _bean_condition("missing_bean", beans)


def matches_conditions(
    target: object, definitions: tuple[BeanDefinition, ...], configuration: Mapping[str, Any],
) -> bool:
    return all(
        condition.matches(definitions, configuration)
        for condition in vars(target).get("__pythonboot_conditions__", ())
    )
