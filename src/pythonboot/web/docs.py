"""OpenAPI documentation UI registration."""

from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse

from pythonboot.exceptions import ConfigurationError

DocsProvider = Literal["scalar", "swagger", "redoc"]


@dataclass(frozen=True)
class DocsOptions:
    enabled: bool
    provider: DocsProvider
    path: str
    openapi_path: str


def resolve_docs_options(configuration: Mapping[str, Any]) -> DocsOptions:
    """Read documentation UI settings from the application configuration."""
    pythonboot = configuration.get("pythonboot", {})
    if not isinstance(pythonboot, Mapping):
        raise ConfigurationError("pythonboot configuration must be a mapping")
    values = pythonboot.get("docs", {})
    if not isinstance(values, Mapping):
        raise ConfigurationError("pythonboot.docs configuration must be a mapping")
    enabled = values.get("enabled", True)
    provider = values.get("provider", "scalar")
    path = values.get("path", "/docs")
    openapi_path = values.get("openapi_path", "/openapi.json")
    if not isinstance(enabled, bool):
        raise ConfigurationError("pythonboot.docs.enabled must be a boolean")
    if provider not in ("scalar", "swagger", "redoc"):
        raise ConfigurationError("pythonboot.docs.provider must be scalar, swagger, or redoc")
    for name, value in (("pythonboot.docs.path", path), ("pythonboot.docs.openapi_path", openapi_path)):
        if not isinstance(value, str) or not value.startswith("/") or value == "/":
            raise ConfigurationError(f"{name} must be an absolute non-root path")
    if path == openapi_path:
        raise ConfigurationError("pythonboot.docs.path and pythonboot.docs.openapi_path must be different")
    return DocsOptions(enabled, provider, path, openapi_path)


def register_api_docs(app: FastAPI, options: DocsOptions) -> None:
    """Register the selected documentation UI for an application."""
    if not options.enabled:
        return
    async def endpoint(request: Request) -> HTMLResponse:
        openapi_url = f"{request.scope.get('root_path', '')}{app.openapi_url}"
        title = f"{app.title} API Reference"
        if options.provider == "swagger":
            return get_swagger_ui_html(openapi_url=openapi_url, title=title)
        if options.provider == "redoc":
            return get_redoc_html(openapi_url=openapi_url, title=title)
        return HTMLResponse(
            "<!doctype html>"
            "<html><head>"
            f"<title>{escape(title)}</title>"
            "</head><body>"
            f'<script id="api-reference" data-url="{escape(openapi_url, quote=True)}"></script>'
            '<script src="https://cdn.jsdelivr.net/npm/@scalar/api-reference"></script>'
            "</body></html>"
        )

    app.add_api_route(options.path, endpoint, methods=["GET"], include_in_schema=False)
