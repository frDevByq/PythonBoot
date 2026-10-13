"""Container access utilities for the current execution context."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, TypeVar

from pythonboot.context import ApplicationContext
from pythonboot.exceptions import ContainerStateError

T = TypeVar("T")
_current_context: ContextVar[ApplicationContext | None] = ContextVar(
    "pythonboot_application_context", default=None,
)


class ContextUtil:
    @staticmethod
    def get_application_context() -> ApplicationContext:
        context = _current_context.get()
        if context is None:
            raise ContainerStateError(
                "No ApplicationContext is bound to the current execution context; "
                "use this utility during requests or application lifespan, "
                "or bind standalone tasks with ContextUtil.use(context)"
            )
        return context

    @staticmethod
    def get_bean(
        bean: type[T] | str, *, name: str | None = None, qualifier: str | None = None,
    ) -> Any:
        return ContextUtil.get_application_context().get_bean(bean, name=name, qualifier=qualifier)

    @staticmethod
    def get_bean_by_name(name: str) -> Any:
        return ContextUtil.get_bean(name)

    @staticmethod
    def get_bean_by_type(bean_type: type[T], *, qualifier: str | None = None) -> T:
        return ContextUtil.get_bean(bean_type, qualifier=qualifier)

    @staticmethod
    async def aget_bean(
        bean: type[T] | str, *, name: str | None = None, qualifier: str | None = None,
    ) -> Any:
        return await ContextUtil.get_application_context().aget_bean(bean, name=name, qualifier=qualifier)

    @staticmethod
    @contextmanager
    def use(context: ApplicationContext) -> Iterator[ApplicationContext]:
        """Temporarily bind a container and restore the previous context on exit."""
        if not isinstance(context, ApplicationContext):
            raise TypeError("context must be an ApplicationContext")
        token = _current_context.set(context)
        try:
            yield context
        finally:
            _current_context.reset(token)
