"""Structured failure metadata; exception text is excluded in production."""
import json
import logging

from .settings import RuntimeSettings


def log_error(logger: logging.Logger, event: str, error: BaseException, *,
              request_id: str | None = None, correlation_id: str | None = None) -> None:
    fields = {"event": event, "request_id": request_id, "correlation_id": correlation_id,
              "exception_type": type(error).__name__}
    debug = RuntimeSettings.from_environment().include_tracebacks
    logger.error(json.dumps(fields, sort_keys=True),
                 exc_info=(type(error), error, error.__traceback__) if debug else None)
