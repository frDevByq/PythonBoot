"""Application-scoped bean proxies and synchronous or asynchronous advice chains."""

import inspect
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

import wrapt

from pythonboot.aop.decorators import AdviceDefinition
from pythonboot.aop.joinpoint import JoinPoint, ProceedingJoinPoint
from pythonboot.aop.pointcut import MethodInfo
from pythonboot.exceptions import AopError


@dataclass(frozen=True)
class Advisor:
    bean_name: str
    aspect_type: type
    method_name: str
    method: Callable[..., Any]
    definition: AdviceDefinition
    aspect_order: int


class BeanProxy(wrapt.ObjectProxy):
    def __init__(self, target: Any, methods: dict[str, Callable[..., Any]]) -> None:
        super().__init__(target)
        self._self_methods = methods

    def __getattr__(self, name: str) -> Any:
        if name in self._self_methods:
            return self._self_methods[name]
        return getattr(self.__wrapped__, name)


class AopEngine:
    def __init__(
        self, beans: tuple[tuple[str, type], ...],
        resolver: Callable[[type, str], Any],
    ) -> None:
        self._resolver = resolver
        advisors: list[Advisor] = []
        for bean_name, cls in beans:
            if not hasattr(cls, "__pythonboot_aspect__"):
                continue
            for method_name, method in inspect.getmembers(cls, inspect.isfunction):
                definitions = getattr(method, "__pythonboot_advices__", ())
                if not definitions:
                    continue
                descriptor = inspect.getattr_static(cls, method_name)
                if isinstance(descriptor, (staticmethod, classmethod)):
                    raise AopError("Aspect advice must use instance methods")
                if inspect.isgeneratorfunction(method) or inspect.isasyncgenfunction(method):
                    raise AopError("Aspect advice does not support generators")
                for definition in definitions:
                    parameter_count = 2 if definition.kind in ("after_returning", "after_throwing") else 1
                    try:
                        inspect.signature(method).bind(object(), *[object() for _ in range(parameter_count)])
                    except TypeError as error:
                        raise AopError(f"Invalid advice signature: {cls.__name__}.{method_name}") from error
                    advisors.append(Advisor(
                        bean_name, cls, method_name, method, definition,
                        cls.__pythonboot_aspect__,
                    ))
        self._advisors = tuple(sorted(advisors, key=lambda item: (
            item.aspect_order, item.definition.order, item.bean_name, item.method_name,
        )))

    def create_proxy(
        self, target: Any, bean_name: str, *, excluded_methods: tuple[str, ...] = (),
    ) -> Any:
        if not self._advisors or hasattr(type(target), "__pythonboot_aspect__"):
            return target
        methods: dict[str, Callable[..., Any]] = {}
        for method_name, method in inspect.getmembers(type(target), inspect.isfunction):
            if method_name.startswith("_") or method_name in excluded_methods:
                continue
            descriptor = inspect.getattr_static(type(target), method_name)
            if isinstance(descriptor, (staticmethod, classmethod)):
                continue
            info = MethodInfo(bean_name, type(target), method_name, method)
            advisors = tuple(item for item in self._advisors if item.definition.pointcut.matches(info))
            if not advisors:
                continue
            if inspect.isgeneratorfunction(method) or inspect.isasyncgenfunction(method):
                raise AopError(f"AOP does not support generator methods: {info.qualified_name}")
            is_async = inspect.iscoroutinefunction(method)
            if not is_async and any(inspect.iscoroutinefunction(item.method) for item in advisors):
                raise AopError(f"Synchronous methods cannot match asynchronous advice: {info.qualified_name}")
            methods[method_name] = self._wrap(getattr(target, method_name), target, bean_name, advisors, is_async)
        return BeanProxy(target, methods) if methods else target

    def _advice(self, advisor: Advisor) -> Callable[..., Any]:
        aspect = self._resolver(advisor.aspect_type, advisor.bean_name)
        return getattr(aspect, advisor.method_name)

    @staticmethod
    def _sync_result(result: Any) -> Any:
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise AopError("Synchronous advice returned an awaitable; use synchronous advice or declare the target method as async")
        return result

    @staticmethod
    async def _async_result(result: Any) -> Any:
        return await result if inspect.isawaitable(result) else result

    def _wrap(
        self, method: Callable[..., Any], target: Any, bean_name: str,
        advisors: tuple[Advisor, ...], is_async: bool,
    ) -> Callable[..., Any]:
        def invoke(index: int, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
            if index == len(advisors):
                return self._sync_result(method(*args, **kwargs))
            advisor = advisors[index]
            advice = self._advice(advisor)
            kind = advisor.definition.kind
            jp = JoinPoint(bean_name, target, method, args, dict(kwargs))

            def proceed(*next_args: Any, **next_kwargs: Any) -> Any:
                return invoke(index + 1, next_args, next_kwargs)

            if kind == "around":
                pjp = ProceedingJoinPoint(bean_name, target, method, args, dict(kwargs), proceed)
                return self._sync_result(advice(pjp))
            if kind == "before":
                self._sync_result(advice(jp))
                return proceed(*jp.args, **jp.kwargs)
            if kind == "after":
                try:
                    return proceed(*jp.args, **jp.kwargs)
                finally:
                    self._sync_result(advice(jp))
            if kind == "after_throwing":
                try:
                    return proceed(*jp.args, **jp.kwargs)
                except BaseException as error:
                    self._sync_result(advice(jp, error))
                    raise
            result = proceed(*jp.args, **jp.kwargs)
            self._sync_result(advice(jp, result))
            return result

        async def invoke_async(index: int, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
            if index == len(advisors):
                return await self._async_result(method(*args, **kwargs))
            advisor = advisors[index]
            advice = self._advice(advisor)
            kind = advisor.definition.kind
            jp = JoinPoint(bean_name, target, method, args, dict(kwargs))

            async def proceed(*next_args: Any, **next_kwargs: Any) -> Any:
                return await invoke_async(index + 1, next_args, next_kwargs)

            if kind == "around":
                pjp = ProceedingJoinPoint(bean_name, target, method, args, dict(kwargs), proceed)
                return await self._async_result(advice(pjp))
            if kind == "before":
                await self._async_result(advice(jp))
                return await proceed(*jp.args, **jp.kwargs)
            if kind == "after":
                try:
                    return await proceed(*jp.args, **jp.kwargs)
                finally:
                    await self._async_result(advice(jp))
            if kind == "after_throwing":
                try:
                    return await proceed(*jp.args, **jp.kwargs)
                except BaseException as error:
                    await self._async_result(advice(jp, error))
                    raise
            result = await proceed(*jp.args, **jp.kwargs)
            await self._async_result(advice(jp, result))
            return result

        if is_async:
            @wraps(method)
            async def endpoint(*args: Any, **kwargs: Any) -> Any:
                return await invoke_async(0, args, kwargs)
        else:
            @wraps(method)
            def endpoint(*args: Any, **kwargs: Any) -> Any:
                return invoke(0, args, kwargs)
        return endpoint
