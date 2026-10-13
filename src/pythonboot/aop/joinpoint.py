"""Context for a method invocation."""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class JoinPoint:
    bean_name: str
    target: Any
    method: Callable[..., Any]
    args: tuple[Any, ...]
    kwargs: dict[str, Any]

    @property
    def method_name(self) -> str:
        return self.method.__name__

    @property
    def qualified_name(self) -> str:
        cls = type(self.target)
        return f"{cls.__module__}.{cls.__qualname__}.{self.method_name}"


@dataclass
class ProceedingJoinPoint(JoinPoint):
    _proceed: Callable[..., Any] = field(repr=False)

    def proceed(self, *args: Any, **kwargs: Any) -> Any:
        """Proceed with current arguments, or replace all arguments when supplied."""
        if not args and not kwargs:
            return self._proceed(*self.args, **self.kwargs)
        return self._proceed(*args, **kwargs)
