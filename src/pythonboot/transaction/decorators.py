"""Declarative transaction metadata compatible with annotation pointcuts."""

from typing import Callable, TypeVar

from pythonboot.aop.pointcut import MethodAnnotation
from pythonboot.transaction.definition import Isolation, Propagation, TransactionAttribute


F = TypeVar("F", bound=Callable)


class Transactional(MethodAnnotation):
    """Mark a method for a resource-specific transaction interceptor."""

    def __call__(
        self,
        method: F | None = None,
        *,
        propagation: Propagation = Propagation.REQUIRED,
        isolation: Isolation = Isolation.DEFAULT,
        timeout: int = -1,
        read_only: bool = False,
        name: str | None = None,
        rollback_for: tuple[type[BaseException], ...] = (Exception,),
        no_rollback_for: tuple[type[BaseException], ...] = (),
        transaction_manager: str | None = None,
    ) -> F | Callable[[F], F]:
        """Support both @transactional and @transactional(...), without wrapping."""
        attribute = TransactionAttribute(
            propagation=propagation, isolation=isolation, timeout=timeout,
            read_only=read_only, name=name, rollback_for=rollback_for,
            no_rollback_for=no_rollback_for, transaction_manager=transaction_manager,
        )

        def decorate(target: F) -> F:
            super(Transactional, self).__call__(target)
            target.__pythonboot_transaction__ = attribute
            return target

        return decorate(method) if method is not None else decorate


transactional = Transactional("pythonboot.transactional")


def get_transaction_attribute(method: Callable) -> TransactionAttribute | None:
    """Read transaction metadata from a function or bound instance method."""
    return getattr(method, "__pythonboot_transaction__", None)
