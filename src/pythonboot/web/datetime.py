"""Date-time request parameter configuration and parsing."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
import json
from types import UnionType
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel, BeforeValidator
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from pythonboot.exceptions import ConfigurationError

DEFAULT_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass(frozen=True)
class DateTimeFormat:
    """Per-parameter date-time format metadata."""

    value: str


def date_time(format: str) -> DateTimeFormat:
    """Set a controller parameter or body field date-time format."""
    if not isinstance(format, str) or not format:
        raise ValueError("date_time format must be a non-empty string")
    return DateTimeFormat(format)


class DateTimeFormatMiddleware:
    """Format serialized JSON date-time values using the application setting."""

    def __init__(self, app: ASGIApp, date_time_format: str) -> None:
        self.app = app
        self.date_time_format = date_time_format

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        start: Message | None = None
        body_parts: list[bytes] = []
        json_response = False

        async def capture(message: Message) -> None:
            nonlocal start, json_response
            if message["type"] == "http.response.start":
                start = message
                json_response = _is_json_response(message)
                if not json_response:
                    await send(message)
                return
            if message["type"] != "http.response.body":
                await send(message)
                return
            if not json_response:
                await send(message)
                return
            body_parts.append(message.get("body", b""))
            if message.get("more_body", False):
                return
            if start is None:
                await send(message)
                return
            body = b"".join(body_parts)
            body = _format_json_date_times(body, self.date_time_format)
            await send(_response_start_with_length(start, len(body)))
            await send({"type": "http.response.body", "body": body, "more_body": False})

        await self.app(scope, receive, capture)


def resolve_datetime_format(configuration: Mapping[str, Any]) -> str:
    """Read the PythonBoot web date-time format setting."""
    pythonboot = configuration.get("pythonboot", {})
    if not isinstance(pythonboot, Mapping):
        raise ConfigurationError("pythonboot configuration must be a mapping")
    web = pythonboot.get("web", {})
    if not isinstance(web, Mapping):
        raise ConfigurationError("pythonboot.web configuration must be a mapping")
    value = web.get("datetime_format", DEFAULT_DATETIME_FORMAT)
    if not isinstance(value, str) or not value:
        raise ConfigurationError("pythonboot.web.datetime_format must be a non-empty string")
    return value


def date_time_annotation(annotation: Any, date_time_format: str) -> Any:
    """Add configured date-time parsing to controller parameters and body models."""
    arguments = get_args(annotation)
    if get_origin(annotation) is Annotated:
        target, *metadata = arguments
    else:
        target, metadata = annotation, []
    format_value = _metadata_format(metadata) or date_time_format
    parser = _date_time_parser(format_value)

    if target is datetime:
        return Annotated[datetime, *metadata, BeforeValidator(parser)]
    if isinstance(target, type) and issubclass(target, BaseModel):
        def normalize_body(value: Any) -> Any:
            return _normalize_model_values(value, target, parser)

        return Annotated[target, *metadata, BeforeValidator(normalize_body)]
    return annotation


def _date_time_parser(format_value: str) -> Any:
    def parse(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return datetime.strptime(value, format_value)
        except ValueError as error:
            raise ValueError(
                f"Date-time value must match the configured format: {format_value}"
            ) from error
    return parse


def _normalize_model_values(value: Any, model_type: type[BaseModel], parser: Any) -> Any:
    """Normalize only declared date-time fields before Pydantic validates a body model."""
    if not isinstance(value, Mapping):
        return value
    return {
        name: _normalize_value(item, _field_annotation(model_type.model_fields[name]), parser)
        if name in model_type.model_fields else item
        for name, item in value.items()
    }


def _normalize_value(value: Any, annotation: Any, parser: Any) -> Any:
    """Recursively normalize date-time fields in nested body values."""
    if annotation is datetime:
        parsed = parser(value)
        return parsed.isoformat() if isinstance(parsed, datetime) else parsed
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Annotated:
        return _normalize_value(
            value, arguments[0], _date_time_parser(_metadata_format(arguments[1:]))
            if _metadata_format(arguments[1:]) else parser,
        )
    if origin in (Union, UnionType):
        date_time_types = [item for item in arguments if item is datetime]
        if date_time_types:
            return _normalize_value(value, date_time_types[0], parser)
        for item in arguments:
            if item is not type(None):
                return _normalize_value(value, item, parser)
        return value
    if origin in (list, set, tuple) and isinstance(value, list) and arguments:
        return [_normalize_value(item, arguments[0], parser) for item in value]
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _normalize_model_values(value, annotation, parser)
    return value


def _metadata_format(metadata: list[Any] | tuple[Any, ...]) -> str | None:
    for item in metadata:
        if isinstance(item, DateTimeFormat):
            return item.value
    return None


def _field_annotation(field: Any) -> Any:
    return Annotated[field.annotation, *field.metadata] if field.metadata else field.annotation


def _is_json_response(message: Message) -> bool:
    return any(
        name.lower() == b"content-type" and b"application/json" in value.lower()
        for name, value in message.get("headers", [])
    )


def _format_json_date_times(body: bytes, date_time_format: str) -> bytes:
    try:
        value = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return body
    return json.dumps(
        _format_value(value, date_time_format), ensure_ascii=False, separators=(",", ":"),
    ).encode()


def _format_value(value: Any, date_time_format: str) -> Any:
    if isinstance(value, list):
        return [_format_value(item, date_time_format) for item in value]
    if isinstance(value, dict):
        return {name: _format_value(item, date_time_format) for name, item in value.items()}
    if not isinstance(value, str) or "T" not in value:
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return parsed.strftime(date_time_format)


def _response_start_with_length(message: Message, length: int) -> Message:
    headers = [
        (name, value) for name, value in message.get("headers", [])
        if name.lower() != b"content-length"
    ]
    headers.append((b"content-length", str(length).encode()))
    return {**message, "headers": headers}
