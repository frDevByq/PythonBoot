"""PythonBoot application creation and startup entry points."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import sys
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI

from pythonboot.beans import scan_components
from pythonboot.boot.autoconfiguration import assemble_auto_configurations
from pythonboot.context import ApplicationContext
from pythonboot.config import load_configuration
from pythonboot.util import ContextUtil
from pythonboot.web import ApplicationContextMiddleware, register_exception_handlers, register_routers


def create_app(
    *, title: str = "PythonBoot", version: str = "0.1.0",
    scan_packages: tuple[str, ...] = (),
    exclude_modules: tuple[str, ...] = (), config_dir: str | Path | None = None,
    auto_configure: bool = True, exclude_auto_configurations: tuple[str, ...] = (),
    exclude: tuple[type, ...] = (),
    **options: Any,
) -> FastAPI:
    """Create an independent application instance."""
    if isinstance(scan_packages, str):
        raise ValueError("scan_packages must be a sequence of package names, not a string")
    if isinstance(exclude, (str, type)) or any(not isinstance(target, type) for target in exclude):
        raise TypeError("exclude must be a sequence of classes")
    excluded_classes = tuple(exclude)
    result = scan_components(
        tuple(scan_packages), exclude_modules=exclude_modules, exclude=excluded_classes,
    )
    configuration = load_configuration(config_dir) if config_dir is not None else {}
    definitions = result.definitions
    if auto_configure:
        definitions = assemble_auto_configurations(
            definitions, result.modules, configuration, exclude=exclude_auto_configurations,
            exclude_classes=excluded_classes,
        )
    context = ApplicationContext(definitions, configuration=configuration)
    app = FastAPI(title=title, version=version, **options)
    app.state.context = context
    native_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[Any]:
        with ContextUtil.use(context):
            await context.start()
            try:
                async with native_lifespan(application) as state:
                    yield state
            finally:
                await context.close()

    app.router.lifespan_context = lifespan
    app.add_middleware(ApplicationContextMiddleware, context=context)
    register_routers(app, result.modules, exclude=excluded_classes)
    register_exception_handlers(app, result.modules, exclude=excluded_classes)
    return app


class PythonBootApplication:
    """Extensible startup class with an independent FastAPI application per instance."""

    def __init__(
        self,
        *,
        title: str = "PythonBoot",
        version: str = "0.1.0",
        scan_packages: tuple[str, ...] | None = None,
        config_dir: str | Path | None = None,
        auto_configure: bool = True,
        exclude_auto_configurations: tuple[str, ...] | None = None,
        exclude: tuple[type, ...] | None = None,
        **options: Any,
    ) -> None:
        packages = (
            scan_packages if scan_packages is not None
            else getattr(type(self), "__pythonboot_scan_packages__", None)
        )
        module_name = type(self).__module__
        module = sys.modules.get(module_name)
        if module_name == "__main__":
            module_name = getattr(getattr(module, "__spec__", None), "name", module_name)
        if packages is None:
            if type(self) is PythonBootApplication:
                packages = ()
            else:
                package_name = getattr(module, "__package__", None) or module_name.rpartition(".")[0]
                if not package_name:
                    raise ValueError("The application class has no importable parent package; set scan_packages explicitly")
                packages = (package_name,)
        self.app: FastAPI = create_app(
            title=title, version=version, scan_packages=packages,
            exclude_modules=(module_name,), config_dir=config_dir,
            auto_configure=auto_configure,
            exclude_auto_configurations=(
                exclude_auto_configurations if exclude_auto_configurations is not None
                else getattr(type(self), "__pythonboot_exclude_auto_configurations__", ())
            ),
            exclude=(
                exclude if exclude is not None else getattr(type(self), "__pythonboot_exclude__", ())
            ),
            **options,
        )
        self.context: ApplicationContext = self.app.state.context
        self.configure(self.app)

    def configure(self, app: FastAPI) -> None:
        """Allow subclasses to register routes, middleware, and exception handlers."""

    def run(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_level: str = "info",
    ) -> None:
        """Start the application; use a Uvicorn module entry for reload or multiple workers."""
        uvicorn.run(self.app, host=host, port=port, log_level=log_level)
