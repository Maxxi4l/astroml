"""Centralized logging configuration for astroml (issue #195).

Every CLI entry point and long-running service should call
:func:`configure_logging` early in startup. It standardises:

- Log level (set via ``ASTROML_LOG_LEVEL`` env var; default ``INFO``).
- Output format (set via ``ASTROML_LOG_FORMAT`` env var: ``text`` for
  human-readable, ``json`` for structured aggregator-friendly output;
  default ``text``).

Modules should keep using ``logging.getLogger(__name__)`` as they already
do — calling :func:`configure_logging` once at startup is the only
required change for the structured output to take effect everywhere.

Replacement for ad-hoc ``logging.basicConfig(...)`` calls scattered
through ingestion services.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Optional


_DEFAULT_LEVEL = "INFO"
_DEFAULT_FORMAT = "text"
_TEXT_FORMAT = "%(asctime)s %(levelname)-7s %(name)s — %(message)s"

# Guard so importing this module twice (or `configure_logging` being called
# from both a library and a CLI entry point) doesn't pile multiple
# StreamHandlers onto the root logger.
_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """One JSON object per log record, structured for log aggregators.

    Avoids a hard dependency on ``python-json-logger`` (which isn't pinned
    in any of the requirements files). The fields are the ones aggregators
    like Datadog / Loki / CloudWatch surface by default.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
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


__all__ = ["configure_logging"]
