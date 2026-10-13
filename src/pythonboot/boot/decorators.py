"""Composite application startup declarations."""

from typing import Callable, TypeVar

T = TypeVar("T", bound=type)


def pythonboot_application(
    cls: T | None = None, *, scan_packages: tuple[str, ...] | None = None,
    exclude_auto_configurations: tuple[str, ...] = (),
    exclude: tuple[type, ...] = (),
) -> T | Callable[[T], T]:
    """Scan the application package by default, or use explicit package patterns."""
    if isinstance(scan_packages, str):
        raise ValueError("scan_packages must be a sequence of package names, not a string")
    packages = tuple(scan_packages) if scan_packages is not None else None
    if packages is not None and any(not isinstance(package, str) or not package for package in packages):
        raise ValueError("Scan package names must be non-empty strings")
    if isinstance(exclude_auto_configurations, str) or any(
        not isinstance(name, str) or not name for name in exclude_auto_configurations
    ):
        raise ValueError("Auto-configuration exclusions must be a sequence of non-empty names")
    exclusions = tuple(exclude_auto_configurations)
    if isinstance(exclude, (str, type)) or any(not isinstance(target, type) for target in exclude):
        raise TypeError("exclude must be a sequence of classes")
    excluded_classes = tuple(exclude)

    def decorate(cls: T) -> T:
        from pythonboot.boot.application import PythonBootApplication

        if not issubclass(cls, PythonBootApplication):
            raise TypeError("Application classes must inherit PythonBootApplication")
        cls.__pythonboot_scan_packages__ = packages
        cls.__pythonboot_exclude_auto_configurations__ = exclusions
        cls.__pythonboot_exclude__ = excluded_classes
        return cls

    return decorate(cls) if cls is not None else decorate
