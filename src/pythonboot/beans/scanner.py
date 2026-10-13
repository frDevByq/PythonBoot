"""Recursive application package scanning with segmented wildcard matching."""

import importlib
import inspect
import sys
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path
from types import ModuleType
from typing import get_type_hints

from pythonboot.beans.definitions import BeanDefinition, ComponentOptions
from pythonboot.exceptions import BeanDefinitionError


@dataclass(frozen=True)
class ScanResult:
    definitions: tuple[BeanDefinition, ...]
    modules: tuple[ModuleType, ...]


def _matches(pattern: tuple[str, ...], name: tuple[str, ...]) -> bool:
    if not pattern:
        return not name
    if pattern[0] == "**":
        return _matches(pattern[1:], name) or (
            bool(name) and _matches(pattern, name[1:])
        )
    return bool(name) and fnmatchcase(name[0], pattern[0]) and _matches(pattern[1:], name[1:])


def _module_names(package: ModuleType) -> set[str]:
    """Discover modules in package paths, including namespace directories."""
    names = {package.__name__}
    for location in getattr(package, "__path__", ()):
        root = Path(location)
        for file in root.rglob("*.py"):
            relative = file.relative_to(root)
            parts = (*relative.parts[:-1], file.stem)
            if any(not part.isidentifier() or part == "__pycache__" for part in parts):
                continue
            if parts[-1] == "__init__":
                parts = parts[:-1]
            for depth in range(1, len(parts) + 1):
                names.add(".".join((package.__name__, *parts[:depth])))
    return names


def scan_components(
    packages: tuple[str, ...], *, exclude_modules: tuple[str, ...] = (),
) -> ScanResult:
    modules: dict[str, ModuleType] = {}
    candidates: set[str] = set()
    for pattern in packages:
        if not isinstance(pattern, str) or not pattern:
            raise BeanDefinitionError("Scan package names must be non-empty strings")
        parts = tuple(pattern.split("."))
        wildcard_index = next((
            index for index, part in enumerate(parts)
            if any(character in part for character in "*?[")
        ), len(parts))
        if not wildcard_index or any(not part.isidentifier() for part in parts[:wildcard_index]):
            raise BeanDefinitionError(f"Scan patterns must start with a concrete package name: {pattern}")
        if any(not part or ("**" in part and part != "**") for part in parts):
            raise BeanDefinitionError(f"Invalid scan pattern: {pattern}")
        package = importlib.import_module(".".join(parts[:wildcard_index]))
        discovered = _module_names(package)
        if wildcard_index == len(parts):
            candidates.update(discovered)
        else:
            candidates.update(name for name in discovered if _matches(parts, tuple(name.split("."))))

    for name in sorted(candidates, key=lambda item: (item.count("."), item)):
        if name in exclude_modules:
            # Reuse the initializing entry module to avoid importing it again under python -m.
            module = sys.modules.get(name)
            main = sys.modules.get("__main__")
            if module is None and getattr(getattr(main, "__spec__", None), "name", None) == name:
                module = main
            if module is not None:
                modules[module.__name__] = module
            continue
        module = importlib.import_module(name)
        modules[module.__name__] = module

    definitions: list[BeanDefinition] = []
    seen: set[int] = set()

    def add_factory(factory: object, owner: type | None = None) -> None:
        options = getattr(factory, "__pythonboot_bean__", None)
        if options is None:
            return
        try:
            bean_type = get_type_hints(factory).get("return")
        except (NameError, TypeError) as error:
            raise BeanDefinitionError(f"Cannot resolve type hints for bean factory {factory}") from error
        if not isinstance(bean_type, type) or bean_type is type(None):
            raise BeanDefinitionError(f"Bean factory {factory} must declare a concrete return type")
        if inspect.iscoroutinefunction(factory) or inspect.isasyncgenfunction(factory):
            raise BeanDefinitionError("Bean factories must create objects synchronously; use init_method for async initialization")
        definitions.append(BeanDefinition(
            name=options.name or factory.__name__,
            bean_type=bean_type,
            factory=factory,
            owner=owner,
            init_method=options.init_method,
            destroy_method=options.destroy_method,
            lazy=options.lazy,
            scope=options.scope,
            primary=options.primary,
            qualifiers=options.qualifiers,
            depends_on=options.depends_on,
        ))

    for module in modules.values():
        for value in vars(module).values():
            if getattr(value, "__module__", None) != module.__name__ or id(value) in seen:
                continue
            seen.add(id(value))
            if inspect.isclass(value):
                options: ComponentOptions | None = vars(value).get("__pythonboot_component__")
                if options is None:
                    continue
                definitions.append(BeanDefinition(
                    name=options.name or value.__name__[:1].lower() + value.__name__[1:],
                    bean_type=value,
                    factory=value,
                    init_method=options.init_method,
                    destroy_method=options.destroy_method,
                    lazy=options.lazy,
                    scope=options.scope,
                    primary=options.primary,
                    qualifiers=options.qualifiers,
                    depends_on=options.depends_on,
                ))
                for method in vars(value).values():
                    if inspect.isfunction(method):
                        add_factory(method, owner=value)
            elif inspect.isfunction(value):
                add_factory(value)

    return ScanResult(tuple(definitions), tuple(modules.values()))
