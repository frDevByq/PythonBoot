"""Application-scoped around advice for declarative transactions."""

from dataclasses import replace
import inspect
from typing import Any, Callable

from pythonboot.aop.decorators import around
from pythonboot.aop.joinpoint import ProceedingJoinPoint
from pythonboot.transaction.decorators import get_transaction_attribute, transactional
from pythonboot.transaction.definition import TransactionAttribute
from pythonboot.transaction.exceptions import IllegalTransactionStateError
from pythonboot.transaction.manager import AsyncPlatformTransactionManager, PlatformTransactionManager


class TransactionInterceptor:
    """Resolve managers from the owning container and complete transaction scopes."""

    def __init__(
        self,
        resolver: Callable[[type, str | None], Any],
        async_resolver: Callable[[type, str | None], Any] | None = None,
    ) -> None:
        self._resolver = resolver
        self._async_resolver = async_resolver

    @around(transactional)
    def invoke(self, join_point: ProceedingJoinPoint) -> Any:
        """Dispatch using the original method's coroutine type."""
        attribute = get_transaction_attribute(join_point.method)
        if attribute is None:
            raise IllegalTransactionStateError("Transaction advice requires transaction metadata")
        if attribute.name is None:
            attribute = replace(attribute, name=join_point.qualified_name)
        if inspect.iscoroutinefunction(join_point.method):
            return self._invoke_async(join_point, attribute)
        return self._invoke_sync(join_point, attribute)

    def _invoke_sync(self, join_point: ProceedingJoinPoint, attribute: TransactionAttribute) -> Any:
        manager = self._resolver(PlatformTransactionManager, attribute.transaction_manager)
        if not isinstance(manager, PlatformTransactionManager):
            raise IllegalTransactionStateError("Synchronous transaction methods require PlatformTransactionManager")
        status = manager.get_transaction(attribute)
        try:
            result = join_point.proceed()
        except BaseException as error:
            if attribute.rollback_on(error):
                manager.rollback(status)
            else:
                manager.commit(status)
            raise
        manager.commit(status)
        return result

    async def _invoke_async(self, join_point: ProceedingJoinPoint, attribute: TransactionAttribute) -> Any:
        if self._async_resolver is None:
            manager = self._resolver(AsyncPlatformTransactionManager, attribute.transaction_manager)
        else:
            manager = await self._async_resolver(AsyncPlatformTransactionManager, attribute.transaction_manager)
        if not isinstance(manager, AsyncPlatformTransactionManager):
            raise IllegalTransactionStateError("Asynchronous transaction methods require AsyncPlatformTransactionManager")
        status = await manager.get_transaction(attribute)
        try:
            result = await join_point.proceed()
        except BaseException as error:
            if attribute.rollback_on(error):
                await manager.rollback(status)
            else:
                await manager.commit(status)
            raise
        await manager.commit(status)
        return result
