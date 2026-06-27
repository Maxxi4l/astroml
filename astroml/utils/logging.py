"""Centralized logging configuration for astroml (issue #195).

Every CLI entry point and long-running service should call
:func:`configure_logging` early in startup. It standardises:

- Log level (set via ``ASTROML_LOG_LEVEL`` env var; default ``INFO``).
- Output format (set via ``ASTROML_LOG_FORMAT`` env var: ``text`` for
  human-readable, ``json`` for structured aggregator-friendly output;
  default ``text``).

Issue #334: Enhanced structured logging with correlation IDs and per-module configuration.

Modules should keep using ``logging.getLogger(__name__)`` as they already
do — calling :func:`configure_logging` once at startup is the only
required change for the structured output to take effect everywhere.

Replacement for ad-hoc ``logging.basicConfig(...)`` calls scattered
through ingestion services.
"""
from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
import uuid
from typing import Optional, Dict


_DEFAULT_LEVEL = "INFO"
_DEFAULT_FORMAT = "text"
_TEXT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s — %(message)s"

# Issue #334: Correlation ID context variable for request tracking
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Issue #334: Per-module log level configuration
_module_log_levels: Dict[str, str] = {}

# Guard so importing this module twice (or `configure_logging` being called
# from both a library and a CLI entry point) doesn't pile multiple
# StreamHandlers onto the root logger.
_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """One JSON object per log record, structured for log aggregators.

    Avoids a hard dependency on ``python-json-logger`` (which isn't pinned
    in any of the requirements files). The fields are the ones aggregators
    like Datadog / Loki / CloudWatch surface by default.
    
    Issue #334: Enhanced with correlation ID support.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Issue #334: Add correlation ID if available
        correlation_id = _correlation_id.get()
        if correlation_id:
            payload["correlation_id"] = correlation_id
        
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Surface any structured `extra={...}` fields the caller passed.
        for key, value in record.__dict__.items():
            if key in payload:
                continue
            if key in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            }:
                continue
            # Only include serialisable values; fall back to repr().
            try:
                json.dumps(value)
                payload[key] = value
            except (TypeError, ValueError):
                payload[key] = repr(value)
        return json.dumps(payload, default=str)


def configure_logging(
    level: Optional[str] = None,
    format: Optional[str] = None,  # noqa: A002 - matches argparse arg name
    force: bool = False,
) -> None:
    """Configure the root logger.

    Parameters
    ----------
    level:
        Log level string (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``,
        ``CRITICAL``). Falls back to ``ASTROML_LOG_LEVEL`` env var, then
        ``INFO``.
    format:
        Either ``"text"`` (human-readable single line) or ``"json"``
        (one JSON object per line). Falls back to ``ASTROML_LOG_FORMAT``
        env var, then ``text``.
    force:
        If True, reconfigure even if :func:`configure_logging` has been
        called already in this process.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    resolved_level = (
        level
        or os.environ.get("ASTROML_LOG_LEVEL")
        or _DEFAULT_LEVEL
    ).upper()
    resolved_format = (
        format
        or os.environ.get("ASTROML_LOG_FORMAT")
        or _DEFAULT_FORMAT
    ).lower()

    handler = logging.StreamHandler(stream=sys.stderr)
    if resolved_format == "json":
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(_TEXT_FORMAT))

    root = logging.getLogger()
    # Clear any previously installed handlers so we don't get duplicate
    # lines when a library called `logging.basicConfig(...)` first.
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(resolved_level)

    _CONFIGURED = True


# Issue #334: Correlation ID management functions
def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set the correlation ID for the current context.
    
    Args:
        correlation_id: Optional correlation ID. If None, generates a new UUID.
        
    Returns:
        The correlation ID that was set.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID from context.
    
    Returns:
        The correlation ID if set, None otherwise.
    """
    return _correlation_id.get()


def clear_correlation_id() -> None:
    """Clear the correlation ID from the current context."""
    _correlation_id.set(None)


# Issue #334: Per-module log level configuration
def set_module_log_level(module_name: str, level: str) -> None:
    """Set log level for a specific module.
    
    Args:
        module_name: The module name (e.g., "astroml.ingestion")
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    _module_log_levels[module_name] = level.upper()
    logger = logging.getLogger(module_name)
    logger.setLevel(level.upper())


def get_module_log_level(module_name: str) -> Optional[str]:
    """Get the configured log level for a specific module.
    
    Args:
        module_name: The module name
        
    Returns:
        The configured log level if set, None otherwise.
    """
    return _module_log_levels.get(module_name)


def configure_module_levels_from_env() -> None:
    """Configure module log levels from environment variable.
    
    Expects ASTROML_MODULE_LOG_LEVELS in format: "module1:DEBUG,module2:INFO"
    """
    env_config = os.environ.get("ASTROML_MODULE_LOG_LEVELS", "")
    if not env_config:
        return
    
    for config in env_config.split(","):
        config = config.strip()
        if ":" not in config:
            continue
        module, level = config.split(":", 1)
        module = module.strip()
        level = level.strip().upper()
        if module and level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            set_module_log_level(module, level)


# Issue #334: Context manager for correlation IDs
class correlation_id:
    """Context manager for setting correlation ID in a scope."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize context manager.
        
        Args:
            correlation_id: Optional correlation ID. If None, generates a new UUID.
        """
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.token = None
    
    def __enter__(self) -> str:
        """Enter context and set correlation ID."""
        self.token = _correlation_id.set(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and restore previous correlation ID."""
        if self.token is not None:
            _correlation_id.reset(self.token)


__all__ = [
    "configure_logging",
    "set_correlation_id",
    "get_correlation_id",
    "clear_correlation_id",
    "set_module_log_level",
    "get_module_log_level",
    "configure_module_levels_from_env",
    "correlation_id",
]
