"""YAML configuration loading and Pydantic settings property binding."""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import inspect
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml
from pydantic_settings import BaseSettings, InitSettingsSource

from pythonboot.beans import component
from pythonboot.exceptions import ConfigurationError

T = TypeVar("T", bound=type)
_configuration_values: ContextVar[Mapping[str, Any]] = ContextVar(
    "pythonboot_configuration_values", default={},
)


@dataclass(frozen=True)
class ConfigurationPropertiesOptions:
    """Configuration metadata attached to a settings bean type."""

    prefix: str


def _merge(target: dict[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        existing = target.get(key)
        if isinstance(existing, dict) and isinstance(value, Mapping):
            _merge(existing, value)
        else:
            target[key] = value
    return target


def _load_yaml_file(file: Path) -> Mapping[str, Any]:
    try:
        with file.open(encoding="utf-8") as stream:
            document = yaml.safe_load(stream)
    except yaml.YAMLError as error:
        raise ConfigurationError(f"Invalid YAML configuration file: {file}") from error
    if document is None:
        return {}
    if not isinstance(document, Mapping):
        raise ConfigurationError(f"YAML configuration root must be a mapping: {file}")
    return document


def _active_profiles(values: Mapping[str, Any]) -> tuple[str, ...]:
    active = values.get("active")
    if active is None:
        return ()
    if not isinstance(active, Mapping):
        raise ConfigurationError("Configuration property active must be a mapping")
    profile = active.get("profile")
    if profile is None:
        return ()
    if isinstance(profile, str):
        profiles = (profile,)
    elif isinstance(profile, Sequence) and not isinstance(profile, (str, bytes)):
        profiles = tuple(profile)
    else:
        raise ConfigurationError("Configuration property active.profile must be a string or sequence of strings")
    if any(
        not isinstance(item, str) or not item or "/" in item or "\\" in item or item in (".", "..")
        for item in profiles
    ):
        raise ConfigurationError("Configuration property active.profile contains an invalid profile name")
    return profiles


def load_configuration(config_dir: str | Path) -> dict[str, Any]:
    """Load application.yml and the active application-{profile}.yml files."""
    directory = Path(config_dir)
    if not directory.is_dir():
        raise ConfigurationError(f"Configuration directory does not exist or is not a directory: {directory}")
    values: dict[str, Any] = {}
    base_file = directory / "application.yml"
    if base_file.is_file():
        _merge(values, _load_yaml_file(base_file))
    for profile in _active_profiles(values):
        profile_file = directory / f"application-{profile}.yml"
        if profile_file.is_file():
            _merge(values, _load_yaml_file(profile_file))
    return values


def _values_for_prefix(prefix: str) -> dict[str, Any]:
    values: Mapping[str, Any] = _configuration_values.get()
    for part in prefix.split("."):
        value = values.get(part)
        if not isinstance(value, Mapping):
            return {}
        values = value
    return dict(values)


@contextmanager
def use_configuration_values(values: Mapping[str, Any]) -> Iterator[None]:
    """Bind application configuration while a bean factory executes."""
    token = _configuration_values.set(values)
    try:
        yield
    finally:
        _configuration_values.reset(token)


def configuration_properties(prefix: str) -> Callable[[T], T]:
    """Register a Pydantic settings class bound to a YAML configuration prefix."""
    normalized_prefix = prefix.strip(".") if isinstance(prefix, str) else ""
    if not normalized_prefix or any(not part for part in normalized_prefix.split(".")):
        raise ValueError("configuration_properties prefix must be a non-empty dotted path")

    def decorate(target: T) -> T:
        if not inspect.isclass(target) or not issubclass(target, BaseSettings):
            raise TypeError("@configuration_properties can only decorate BaseSettings subclasses")
        if "__pythonboot_configuration_properties__" in vars(target):
            raise ConfigurationError(f"Configuration properties already declared for {target.__name__}")
        if "__pythonboot_component__" not in vars(target):
            component(target)
        target.__pythonboot_configuration_properties__ = ConfigurationPropertiesOptions(normalized_prefix)
        original_sources = target.settings_customise_sources

        @classmethod
        def settings_customise_sources(
            cls: type[BaseSettings], settings_cls: type[BaseSettings], init_settings: Any, env_settings: Any,
            dotenv_settings: Any, file_secret_settings: Any,
        ) -> tuple[Any, ...]:
            sources = original_sources(
                settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
            )
            yaml_settings = InitSettingsSource(
                settings_cls, init_kwargs=_values_for_prefix(normalized_prefix),
            )
            try:
                index = sources.index(env_settings) + 1
            except ValueError:
                index = len(sources)
            return (*sources[:index], yaml_settings, *sources[index:])

        target.settings_customise_sources = settings_customise_sources
        return target

    return decorate
