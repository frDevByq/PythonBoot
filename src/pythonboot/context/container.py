"""Application container, bean scopes, dependency resolution, and lifecycle."""

import asyncio
import inspect
from dataclasses import dataclass, field
from threading import RLock
from types import UnionType
from typing import Annotated, Any, Mapping, Union, get_args, get_origin, get_type_hints

from pythonboot.aop.proxy import AopEngine
from pythonboot.beans import BeanDefinition
from pythonboot.beans.lifecycle import get_ondestroy_methods, get_postconstruct_methods
from pythonboot.context.injection import Autowired, LazyDependency
from pythonboot.config.properties import use_configuration_values
from pythonboot.exceptions import (
    BeanDefinitionError, CircularDependencyError, ContainerStateError,
    DuplicateBeanError, MissingBeanError,
)


@dataclass(eq=False)
class _BeanState:
    definition: BeanDefinition
    instance: Any
    dependencies: list["_BeanState"] = field(default_factory=list)
    explicit_dependencies: list["_BeanState"] = field(default_factory=list)
    complete: bool = False
    initialized: bool = False
    initializing: bool = False
    failure: BaseException | None = None
    init_methods: tuple[str, ...] = ()
    destroy_methods: tuple[str, ...] = ()


class ApplicationContext:
    def __init__(
        self, definitions: tuple[BeanDefinition, ...] = (), *, configuration: Mapping[str, Any] | None = None,
    ) -> None:
        self._definitions: dict[str, BeanDefinition] = {}
        self._singletons: dict[str, _BeanState] = {}
        self._creation_order: list[_BeanState] = []
        self._startup_states: list[_BeanState] = []
        self._resolving: list[str] = []
        self._failures: dict[str, BaseException] = {}
        self._active = False
        self._started = False
        self._starting = False
        self._lock = RLock()
        self._async_init_lock = asyncio.Lock()
        self._init_owner: asyncio.Task[Any] | None = None
        self._configuration = configuration or {}
        for definition in definitions:
            if definition.name in self._definitions:
                raise DuplicateBeanError(f"Duplicate bean name: {definition.name}")
            self._definitions[definition.name] = definition
        self._validate_depends_on()
        self._aop = AopEngine(
            tuple((item.name, item.bean_type) for item in self._definitions.values()),
            lambda bean_type, name: self.get_bean(bean_type, name=name),
            async_resolver=lambda bean_type, name: self.aget_bean(bean_type, name=name),
        )

    def _validate_depends_on(self) -> None:
        visited: set[str] = set()
        path: list[str] = []

        def visit(name: str) -> None:
            if name in path:
                raise CircularDependencyError("Circular depends_on dependency: " + " -> ".join([*path, name]))
            if name in visited:
                return
            definition = self._definitions.get(name)
            if definition is None:
                raise MissingBeanError(f"Bean specified in depends_on does not exist: {name}")
            path.append(name)
            for dependency in definition.depends_on:
                visit(dependency)
            path.pop()
            visited.add(name)

        for name in self._definitions:
            visit(name)

    def get_bean(
        self, bean_type: type | str, *, name: str | None = None, qualifier: str | None = None,
    ) -> Any:
        with self._lock:
            self._check_active()
            state = self._resolve(self._find_definition(bean_type, name=name, qualifier=qualifier))
            if self._started or self._init_owner is not None:
                self._initialize_sync(state, set())
            return state.instance

    async def aget_bean(
        self, bean_type: type | str, *, name: str | None = None, qualifier: str | None = None,
    ) -> Any:
        """Get a bean and await dependency initialization; create prototypes per lookup."""
        if self._init_owner is asyncio.current_task():
            with self._lock:
                self._check_active()
                state = self._resolve(self._find_definition(bean_type, name=name, qualifier=qualifier))
            await self._initialize_async(state, set())
            return state.instance
        async with self._async_init_lock:
            self._init_owner = asyncio.current_task()
            try:
                with self._lock:
                    self._check_active()
                    state = self._resolve(self._find_definition(bean_type, name=name, qualifier=qualifier))
                await self._initialize_async(state, set())
                return state.instance
            finally:
                self._init_owner = None

    def _check_active(self) -> None:
        if not self._active:
            raise ContainerStateError("The container is not active; obtain beans during application lifespan or requests")

    def _find_definition(
        self, bean_type: type | str, *, name: str | None = None, qualifier: str | None = None,
    ) -> BeanDefinition:
        if isinstance(bean_type, str):
            if name is not None and name != bean_type:
                raise BeanDefinitionError("Named bean lookup cannot specify a different name")
            definition = self._definitions.get(bean_type)
            if definition is None or (
                qualifier is not None and qualifier != definition.name
                and qualifier not in definition.qualifiers
            ):
                raise MissingBeanError(f"Missing bean: {bean_type}, qualifier: {qualifier}")
            return definition
        if not isinstance(bean_type, type):
            raise BeanDefinitionError(f"Dependency types must be concrete classes: {bean_type}")
        candidates = [
            item for item in self._definitions.values()
            if issubclass(item.bean_type, bean_type)
            and (name is None or item.name == name)
            and (qualifier is None or qualifier == item.name or qualifier in item.qualifiers)
        ]
        if not candidates:
            raise MissingBeanError(
                f"Missing bean: {bean_type.__qualname__}, name: {name}, qualifier: {qualifier}"
            )
        if len(candidates) > 1:
            primary = [item for item in candidates if item.primary]
            if len(primary) == 1:
                return primary[0]
            raise DuplicateBeanError(
                f"Multiple candidates for bean type {bean_type.__qualname__}: "
                + ", ".join(item.name for item in candidates)
            )
        return candidates[0]

    @staticmethod
    def _dependency_type(annotation: Any) -> Any:
        if get_origin(annotation) is Annotated:
            annotation = get_args(annotation)[0]
        if get_origin(annotation) in (Union, UnionType):
            types = tuple(item for item in get_args(annotation) if item is not type(None))
            if len(types) == 1:
                annotation = types[0]
        return annotation

    def _resolve(self, definition: BeanDefinition) -> _BeanState:
        name = definition.name
        singleton = definition.scope == "singleton"
        if singleton and name in self._failures:
            raise self._failures[name]
        if singleton and name in self._singletons:
            state = self._singletons[name]
            if state.failure is not None:
                raise state.failure
            return state
        if name in self._resolving:
            raise CircularDependencyError("Circular dependency: " + " -> ".join([*self._resolving, name]))
        self._resolving.append(name)
        state: _BeanState | None = None
        try:
            explicit_dependencies = [self._resolve(self._definitions[item]) for item in definition.depends_on]
            dependencies = list(explicit_dependencies)
            factory = definition.factory
            if definition.owner is not None:
                owner = self._resolve(self._find_definition(definition.owner))
                dependencies.append(owner)
                factory = factory.__get__(owner.instance, definition.owner)
            kwargs: dict[str, Any] = {}
            configuration_properties = (
                inspect.isclass(factory)
                and "__pythonboot_configuration_properties__" in vars(factory)
            )
            hint_source = factory.__init__ if inspect.isclass(factory) else factory
            try:
                hints = {} if configuration_properties else get_type_hints(hint_source, include_extras=True)
            except (NameError, TypeError) as error:
                raise BeanDefinitionError(f"Cannot resolve dependency type hints for bean {name}") from error
            parameters = () if configuration_properties else inspect.signature(factory).parameters.values()
            for parameter in parameters:
                if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
                    continue
                if parameter.kind == parameter.POSITIONAL_ONLY:
                    raise BeanDefinitionError(f"Bean {name} does not support positional-only parameter: {parameter.name}")
                annotation = hints.get(parameter.name)
                marker = None
                if get_origin(annotation) is Annotated:
                    marker = next((item for item in get_args(annotation)[1:] if isinstance(item, Autowired)), None)
                if marker is not None and marker.lazy:
                    raise BeanDefinitionError("Lazy constructor injection is not supported; use an autowired(lazy=True) attribute")
                dependency_type = self._dependency_type(annotation)
                if dependency_type is None:
                    if parameter.default is not parameter.empty:
                        continue
                    raise BeanDefinitionError(f"Parameter {parameter.name} of bean {name} has no type annotation")
                try:
                    dependency_definition = self._find_definition(
                        dependency_type,
                        name=marker.name if marker else None,
                        qualifier=marker.qualifier if marker else None,
                    )
                except MissingBeanError:
                    if parameter.default is not parameter.empty:
                        continue
                    if marker is not None and not marker.required:
                        kwargs[parameter.name] = None
                        continue
                    raise
                dependency = self._resolve(dependency_definition)
                dependencies.append(dependency)
                kwargs[parameter.name] = dependency.instance
            with use_configuration_values(self._configuration):
                instance = factory(**kwargs)
            if not isinstance(instance, definition.bean_type):
                raise BeanDefinitionError(f"Factory return type mismatch for bean {name}")
            init_methods = tuple(dict.fromkeys((
                *get_postconstruct_methods(type(instance)),
                *((definition.init_method,) if definition.init_method is not None else ()),
            )))
            destroy_methods = tuple(dict.fromkeys((
                *get_ondestroy_methods(type(instance)),
                *((definition.destroy_method,) if definition.destroy_method is not None else ()),
            )))
            proxy = self._aop.create_proxy(
                instance, name, excluded_methods=tuple(method for method in (
                    *init_methods, *destroy_methods,
                ) if method is not None),
            )
            state = _BeanState(
                definition, proxy, dependencies, explicit_dependencies,
                init_methods=init_methods, destroy_methods=destroy_methods,
            )
            if singleton:
                # Publish singleton proxies early for attribute cycles; do not expose prototypes early.
                self._singletons[name] = state
                self._creation_order.append(state)
            if self._starting:
                self._startup_states.append(state)
            self._inject_properties(instance, state)
            state.complete = True
            return state
        except BaseException as error:
            if state is not None:
                state.failure = error
            if singleton:
                self._failures[name] = error
            raise
        finally:
            self._resolving.pop()

    def _inject_properties(self, instance: Any, state: _BeanState) -> None:
        members: dict[str, Any] = {}
        for cls in reversed(type(instance).__mro__):
            members.update(vars(cls))
        fields = {name: value for name, value in members.items() if isinstance(value, Autowired)}
        if not fields:
            return
        try:
            hints = get_type_hints(type(instance), include_extras=True)
        except (NameError, TypeError) as error:
            raise BeanDefinitionError(f"Cannot resolve attribute type hints for bean {state.definition.name}") from error
        for attribute, marker in fields.items():
            dependency_type = self._dependency_type(hints.get(attribute))
            if not isinstance(dependency_type, type):
                raise BeanDefinitionError(
                    f"Injected attribute {attribute} of bean {state.definition.name} must declare a concrete dependency type"
                )
            try:
                definition = self._find_definition(dependency_type, name=marker.name, qualifier=marker.qualifier)
            except MissingBeanError:
                if marker.required:
                    raise
                value = None
            else:
                if marker.lazy:
                    value = LazyDependency(
                        lambda bean_type=dependency_type, name=definition.name:
                        self.get_bean(bean_type, name=name)
                    )
                else:
                    dependency = self._resolve(definition)
                    state.dependencies.append(dependency)
                    value = dependency.instance
            setattr(instance, attribute, value)

    @staticmethod
    def _hook(state: _BeanState, method_name: str | None) -> Any:
        if method_name is None:
            return None
        method = getattr(state.instance, method_name, None)
        if not callable(method):
            raise BeanDefinitionError(f"Bean {state.definition.name} has no callable lifecycle method: {method_name}")
        return method

    def _initialize_sync(self, state: _BeanState, visiting: set[_BeanState]) -> None:
        if state.failure is not None:
            raise state.failure
        if state.initialized or state in visiting:
            return
        if not state.complete:
            raise ContainerStateError(f"Attribute injection is incomplete for bean {state.definition.name}")
        if self._init_owner is not None:
            try:
                task = asyncio.current_task()
            except RuntimeError:
                task = None
            if task is not self._init_owner:
                raise ContainerStateError("Bean initialization is running asynchronously; use await context.aget_bean(...)")
        if state.initializing:
            return
        methods = [self._hook(state, name) for name in state.init_methods]
        if any(inspect.iscoroutinefunction(method) for method in methods):
            raise ContainerStateError(
                f"Bean {state.definition.name} requires asynchronous initialization; use await context.aget_bean(...)"
            )
        visiting.add(state)
        state.initializing = True
        try:
            for dependency in state.dependencies:
                self._initialize_sync(dependency, visiting)
            if any(not dependency.initialized for dependency in state.explicit_dependencies):
                raise CircularDependencyError(f"depends_on and instance dependencies form an initialization cycle for bean {state.definition.name}")
            for method in methods:
                result = method()
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result):
                        result.close()
                    raise BeanDefinitionError("Synchronous initialization returned an awaitable; declare the initializer as async")
            state.initialized = True
        except ContainerStateError:
            raise
        except BaseException as error:
            state.failure = error
            raise
        finally:
            state.initializing = False
            visiting.discard(state)

    async def _initialize_async(self, state: _BeanState, visiting: set[_BeanState]) -> None:
        if state.failure is not None:
            raise state.failure
        if state.initialized or state.initializing or state in visiting:
            return
        if not state.complete:
            raise ContainerStateError(f"Attribute injection is incomplete for bean {state.definition.name}")
        visiting.add(state)
        state.initializing = True
        try:
            for dependency in state.dependencies:
                await self._initialize_async(dependency, visiting)
            if any(not dependency.initialized for dependency in state.explicit_dependencies):
                raise CircularDependencyError(f"depends_on and instance dependencies form an initialization cycle for bean {state.definition.name}")
            for name in state.init_methods:
                method = self._hook(state, name)
                result = method()
                if inspect.isawaitable(result):
                    await result
            state.initialized = True
        except BaseException as error:
            state.failure = error
            raise
        finally:
            state.initializing = False
            visiting.discard(state)

    async def start(self) -> None:
        if self._active:
            raise ContainerStateError("The container is already active")
        self._active = True
        self._starting = True
        try:
            for definition in self._definitions.values():
                if definition.scope == "singleton" and not definition.lazy:
                    self._resolve(definition)
            async with self._async_init_lock:
                self._init_owner = asyncio.current_task()
                try:
                    for state in self._startup_states:
                        await self._initialize_async(state, set())
                finally:
                    self._init_owner = None
            self._started = True
        except BaseException:
            await self.close()
            raise
        finally:
            self._starting = False
            self._startup_states.clear()

    async def close(self) -> None:
        self._active = False
        self._started = False
        errors: list[Exception] = []
        try:
            for state in reversed(self._creation_order):
                try:
                    for name in state.destroy_methods:
                        method = self._hook(state, name)
                        result = method() if method is not None else None
                        if inspect.isawaitable(result):
                            await result
                except Exception as error:
                    errors.append(error)
        finally:
            self._singletons.clear()
            self._creation_order.clear()
            self._startup_states.clear()
            self._failures.clear()
        if errors:
            raise ExceptionGroup("Bean destruction failed", errors)
