"""Container integration preserving native FastAPI routing and dependencies."""

import inspect
from functools import wraps
from types import ModuleType
from typing import Any, Callable, TypeVar, get_type_hints

from fastapi import APIRouter, FastAPI, Request

from pythonboot.exceptions import BeanDefinitionError

T = TypeVar("T")


def inject(
    bean_type: type[T], *, name: str | None = None, qualifier: str | None = None,
) -> Callable[[Request], T]:
    """Use Depends(inject(Service)) to resolve a bean according to its scope."""
    def dependency(request: Request) -> T:
        return request.app.state.context.get_bean(bean_type, name=name, qualifier=qualifier)

    return dependency


def _controller_endpoint(cls: type, method: Callable[..., Any]) -> Callable[..., Any]:
    """Hide self and resolve the current application's controller for each request."""
    signature = inspect.signature(method)
    parameters = list(signature.parameters.values())
    if not parameters or parameters[0].name != "self":
        raise BeanDefinitionError(f"Controller route {cls.__name__}.{method.__name__} must be an instance method")
    parameters = parameters[1:]
    if any(parameter.kind in (
        parameter.POSITIONAL_ONLY, parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD,
    ) for parameter in parameters):
        raise BeanDefinitionError("Controller routes do not support positional-only parameters, *args, or **kwargs")
    try:
        hints = get_type_hints(method, include_extras=True)
    except (NameError, TypeError) as error:
        raise BeanDefinitionError(f"Cannot resolve type hints for controller route {cls.__name__}.{method.__name__}") from error
    parameters = [
        parameter.replace(annotation=hints.get(parameter.name, parameter.annotation))
        for parameter in parameters
    ]
    request_name = "_pythonboot_request"
    while request_name in signature.parameters:
        request_name += "_"
    parameters.append(inspect.Parameter(
        request_name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=Request,
    ))
    component_options = vars(cls)["__pythonboot_component__"]
    bean_name = component_options.name or cls.__name__[:1].lower() + cls.__name__[1:]

    def bound_method(kwargs: dict[str, Any]) -> Callable[..., Any]:
        request: Request = kwargs.pop(request_name)
        instance = request.app.state.context.get_bean(cls, name=bean_name)
        return getattr(instance, method.__name__)

    if inspect.iscoroutinefunction(method):
        @wraps(method)
        async def endpoint(*args: Any, **kwargs: Any) -> Any:
            target = bound_method(kwargs)
            return await target(*args, **kwargs)
    else:
        @wraps(method)
        def endpoint(*args: Any, **kwargs: Any) -> Any:
            target = bound_method(kwargs)
            return target(*args, **kwargs)

    endpoint.__name__ = f"{cls.__name__}_{method.__name__}"
    endpoint.__signature__ = signature.replace(
        parameters=parameters,
        return_annotation=hints.get("return", signature.return_annotation),
    )
    return endpoint


def register_routers(app: FastAPI, modules: tuple[ModuleType, ...]) -> None:
    """Automatically register class-based controllers and native APIRouter objects."""
    seen: set[int] = set()
    for module in modules:
        for value in vars(module).values():
            if isinstance(value, APIRouter) and id(value) not in seen:
                seen.add(id(value))
                app.include_router(value)
            elif (
                inspect.isclass(value)
                and value.__module__ == module.__name__
                and "__pythonboot_controller__" in vars(value)
                and id(value) not in seen
            ):
                seen.add(id(value))
                router = APIRouter(**vars(value)["__pythonboot_controller__"])
                for _, method in inspect.getmembers(value, inspect.isfunction):
                    definitions = getattr(method, "__pythonboot_routes__", ())
                    if not definitions:
                        continue
                    endpoint = _controller_endpoint(value, method)
                    for definition in definitions:
                        router.add_api_route(
                            definition.path, endpoint,
                            methods=list(definition.methods), **definition.options,
                        )
                app.include_router(router)
