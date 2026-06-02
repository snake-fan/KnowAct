import logging
from typing import TextIO


KNOWACT_LOGGER_NAME = "knowact"
_CONSOLE_HANDLER_MARKER = "_knowact_console_handler"
_UVICORN_CONSOLE_FORMAT = "%(levelprefix)s %(name)s: %(message)s"
_FALLBACK_CONSOLE_FORMAT = "%(levelname)-8s %(name)s: %(message)s"

logging.getLogger(KNOWACT_LOGGER_NAME).addHandler(logging.NullHandler())


def configure_knowact_logging(
    level: int = logging.INFO,
    *,
    stream: TextIO | None = None,
    use_colors: bool | None = None,
) -> None:
    logger = logging.getLogger(KNOWACT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not any(getattr(handler, _CONSOLE_HANDLER_MARKER, False) for handler in logger.handlers):
        handler = logging.StreamHandler(stream)
        setattr(handler, _CONSOLE_HANDLER_MARKER, True)
        logger.addHandler(handler)

    for handler in logger.handlers:
        if getattr(handler, _CONSOLE_HANDLER_MARKER, False):
            handler.setLevel(level)
            handler.setFormatter(_build_console_formatter(use_colors=use_colors))


def get_knowact_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{KNOWACT_LOGGER_NAME}.{name}")


def _build_console_formatter(*, use_colors: bool | None = None) -> logging.Formatter:
    try:
        from uvicorn.logging import DefaultFormatter
    except ImportError:
        return logging.Formatter(_FALLBACK_CONSOLE_FORMAT)

    return DefaultFormatter(_UVICORN_CONSOLE_FORMAT, use_colors=use_colors)
