"""Explicit attribute injection declarations."""

from typing import Any, Callable

from pythonboot.exceptions import BeanDefinitionError, ContainerStateError


class LazyDependency:
    def __init__(self, resolver: Callable[[], Any]) -> None:
        self._resolver = resolver

    def resolve(self) -> Any:
        return self._resolver()


class Autowired:
    def __init__(
        self, *, name: str | None = None, required: bool = True, lazy: bool = False,
        qualifier: str | None = None,
    ) -> None:
        self.name = name
        self.required = required
        self.lazy = lazy
        self.qualifier = qualifier
        self._attribute_name = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self._attribute_name = name

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        try:
            attributes = vars(instance)
        except TypeError as error:
            raise BeanDefinitionError("Attribute injection requires instances with __dict__") from error
        if self._attribute_name not in attributes:
            raise ContainerStateError(
                f"Attribute {type(instance).__name__}.{self._attribute_name} has not been injected; "
                "access it in initialization or business methods, not in the constructor"
            )
        value = attributes[self._attribute_name]
        if isinstance(value, LazyDependency):
            value = value.resolve()
            attributes[self._attribute_name] = value
        return value

    def __set__(self, instance: Any, value: Any) -> None:
        try:
            vars(instance)[self._attribute_name] = value
        except TypeError as error:
            raise BeanDefinitionError("Attribute injection requires instances with __dict__") from error


def autowired(
    *, name: str | None = None, required: bool = True, lazy: bool = False,
    qualifier: str | None = None,
) -> Any:
    """Declare a dependency injected by attribute type, with an optional bean name."""
    return Autowired(name=name, required=required, lazy=lazy, qualifier=qualifier)
