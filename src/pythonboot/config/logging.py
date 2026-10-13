"""Application logging configuration."""

from collections.abc import Mapping
from copy import copy
import logging
import logging.config
import sys
from typing import Any

from pythonboot.exceptions import ConfigurationError

DEFAULT_LOG_FORMAT = (
    "%(asctime)s.%(msecs)03d %(levelname)-5s %(process)5d "
    "[Thread-%(thread)d] %(name)s : %(message)s"
)
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",
    logging.INFO: "\033[32m",
    logging.WARNING: "\033[33m",
    logging.ERROR: "\033[31m",
    logging.CRITICAL: "\033[31m",
}
_RESET_COLOR = "\033[0m"


class ConsoleFormatter(logging.Formatter):
    """Render log levels with terminal colors when supported."""

    def __init__(self, *args: Any, colors: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._colors = colors

    def format(self, record: logging.LogRecord) -> str:
        if not self._colors:
            return super().format(record)
        colored_record = copy(record)
        color = _LEVEL_COLORS.get(record.levelno)
        if color is not None:
            colored_record.levelname = f"{color}{record.levelname:<5}{_RESET_COLOR}"
        return super().format(colored_record)


def _log_level(value: Any) -> int:
    if not isinstance(value, str) or value.upper() not in logging.getLevelNamesMapping():
        raise ConfigurationError("logging.level must be a valid logging level name")
    return logging.getLevelNamesMapping()[value.upper()]


def _apply_formatter(formatter: logging.Formatter) -> None:
    for logger_name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
        for handler in logging.getLogger(logger_name).handlers:
            handler.setFormatter(formatter)


def configure_logging(configuration: Mapping[str, Any]) -> None:
    """Configure logging from the application logging section."""
    pythonboot = configuration.get("pythonboot", {})
    if not isinstance(pythonboot, Mapping):
        raise ConfigurationError("pythonboot configuration must be a mapping")
    options = pythonboot.get("logging", {})
    if not isinstance(options, Mapping):
        raise ConfigurationError("pythonboot.logging configuration must be a mapping")
    if "version" in options:
        try:
            logging.config.dictConfig(dict(options))
        except (TypeError, ValueError) as error:
            raise ConfigurationError("Invalid logging dictConfig configuration") from error
        return

    allowed = {"level", "format", "date_format", "colors", "loggers"}
    unexpected = set(options).difference(allowed)
    if unexpected:
        raise ConfigurationError("Unsupported logging options: " + ", ".join(sorted(unexpected)))
    level = _log_level(options.get("level", "INFO"))
    log_format = options.get("format", DEFAULT_LOG_FORMAT)
    date_format = options.get("date_format", DEFAULT_DATE_FORMAT)
    colors = options.get("colors", sys.stdout.isatty())
    if not isinstance(log_format, str) or not isinstance(date_format, str) or not isinstance(colors, bool):
        raise ConfigurationError("logging.format and logging.date_format must be strings; logging.colors must be a boolean")
    logging.basicConfig(level=level, format=log_format, datefmt=date_format, stream=sys.stdout)
    logging.getLogger().setLevel(level)
    _apply_formatter(ConsoleFormatter(log_format, datefmt=date_format, colors=colors))
    logger_levels = options.get("loggers", {})
    if not isinstance(logger_levels, Mapping):
        raise ConfigurationError("logging.loggers must be a mapping of logger names to levels")
    for name, logger_level in logger_levels.items():
        if not isinstance(name, str) or not name:
            raise ConfigurationError("logging.loggers keys must be non-empty strings")
        logging.getLogger(name).setLevel(_log_level(logger_level))
