"""Discover installed starter entry points and assemble conditional bean definitions."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib.metadata import entry_points
import inspect
from types import ModuleType
from typing import Any, TypeVar

from pythonboot.beans.conditions import matches_conditions
from pythonboot.beans.definitions import BeanDefinition, component
from pythonboot.beans.scanner import collect_definitions
from pythonboot.exceptions import BeanDefinitionError

T = TypeVar("T", bound=type)


@dataclass(frozen=True)
class AutoConfigurationOptions:
    order: int = 0
    imports: tuple[type, ...] = ()


def auto_configuration(
    cls: T | None = None, *, order: int = 0, imports: tuple[type, ...] = (),
) -> T | Callable[[T], T]:
    """Declare a starter configuration and its explicitly imported companion beans."""
    if not isinstance(order, int):
        raise TypeError("Auto-configuration order must be an integer")
    if any(not inspect.isclass(target) for target in imports):
        raise TypeError("Auto-configuration imports must contain classes")

    def decorate(target: T) -> T:
        if not inspect.isclass(target):
            raise TypeError("@auto_configuration can only decorate classes")
        if "__pythonboot_component__" not in vars(target):
            component(target)
        target.__pythonboot_auto_configuration__ = AutoConfigurationOptions(order, tuple(imports))
        return target

    return decorate(cls) if cls is not None else decorate


def assemble_auto_configurations(
    definitions: tuple[BeanDefinition, ...], modules: tuple[ModuleType, ...],
    configuration: Mapping[str, Any], *, exclude: tuple[str, ...] = (),
    exclude_classes: tuple[type, ...] = (),
) -> tuple[BeanDefinition, ...]:
    """Apply user definitions first, then ordered, explicitly advertised configurations."""
    if isinstance(exclude, str) or any(not isinstance(name, str) or not name for name in exclude):
        raise ValueError("Auto-configuration exclusions must be a sequence of non-empty names")
    candidates: dict[str, type] = {}
    excluded_classes = set(exclude_classes)
    excluded_names = {f"{target.__module__}.{target.__qualname__}" for target in excluded_classes}

    def add(target: object) -> None:
        if isinstance(target, ModuleType):
            for value in vars(target).values():
                if inspect.isclass(value) and "__pythonboot_auto_configuration__" in vars(value):
                    add(value)
            return
        if not inspect.isclass(target) or "__pythonboot_auto_configuration__" not in vars(target):
            raise BeanDefinitionError("Auto-configuration entry points must reference decorated classes or modules")
        name = f"{target.__module__}.{target.__qualname__}"
        if name not in exclude and target not in excluded_classes:
            candidates[name] = target

    for module in modules:
        add(module)
    for entry in sorted(entry_points(group="pythonboot.autoconfigure"), key=lambda item: (item.name, item.value)):
        qualified_name = entry.value.split("[", 1)[0].strip().replace(":", ".")
        if entry.name in exclude or qualified_name in exclude or qualified_name in excluded_names:
            continue
        try:
            add(entry.load())
        except Exception as error:
            raise BeanDefinitionError(f"Cannot load auto-configuration entry point {entry.name}: {entry.value}") from error

    registered = list(definitions)
    sources = {(id(item.factory), item.owner) for item in definitions}
    for name, target in sorted(
        candidates.items(), key=lambda item: (vars(item[1])["__pythonboot_auto_configuration__"].order, item[0]),
    ):
        if not matches_conditions(target, tuple(registered), configuration):
            continue
        options: AutoConfigurationOptions = vars(target)["__pythonboot_auto_configuration__"]
        companions = tuple(
            imported for imported in options.imports
            if imported not in excluded_classes
            and matches_conditions(imported, tuple(registered), configuration)
        )
        def include_factory(factory: object) -> bool:
            return all(
                condition.matches(tuple(registered), configuration)
                for condition in vars(factory).get("__pythonboot_conditions__", ())
                if condition.kind in ("module", "property")
            )

        pending = collect_definitions(
            (*companions, target), include_factory=include_factory, exclude=exclude_classes,
        )
        # Unconditional definitions precede bean-dependent fallback factories.
        pending = tuple(sorted(pending, key=lambda item: any(
            condition.kind in ("bean", "missing_bean")
            for condition in vars(item.factory).get("__pythonboot_conditions__", ())
        )))
        for definition in pending:
            source = (id(definition.factory), definition.owner)
            if source in sources:
                continue
            if definition.factory is not target and not matches_conditions(
                definition.factory, tuple(registered), configuration,
            ):
                continue
            registered.append(definition)
            sources.add(source)
    return tuple(registered)
