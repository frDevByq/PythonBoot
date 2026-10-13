"""Composite application startup declarations."""

from typing import Callable, TypeVar

T = TypeVar("T", bound=type)


def pythonboot_application(
    cls: T | None = None, *, scan_packages: tuple[str, ...] | None = None,
) -> T | Callable[[T], T]:
    """Scan the application package by default, or use explicit package patterns."""
    if isinstance(scan_packages, str):
        raise ValueError("scan_packages must be a sequence of package names, not a string")
    packages = tuple(scan_packages) if scan_packages is not None else None
    if packages is not None and any(not isinstance(package, str) or not package for package in packages):
        raise ValueError("Scan package names must be non-empty strings")

    def decorate(cls: T) -> T:
        from pythonboot.boot.application import PythonBootApplication

        if not issubclass(cls, PythonBootApplication):
            raise TypeError("Application classes must inherit PythonBootApplication")
        cls.__pythonboot_scan_packages__ = packages
        return cls

    return decorate(cls) if cls is not None else decorate
