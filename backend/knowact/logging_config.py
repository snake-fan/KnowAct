import logging


KNOWACT_LOGGER_NAME = "knowact"
_CONSOLE_HANDLER_MARKER = "_knowact_console_handler"

logging.getLogger(KNOWACT_LOGGER_NAME).addHandler(logging.NullHandler())


def configure_knowact_logging(level: int = logging.INFO) -> None:
    logger = logging.getLogger(KNOWACT_LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if not any(getattr(handler, _CONSOLE_HANDLER_MARKER, False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        setattr(handler, _CONSOLE_HANDLER_MARKER, True)
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        logger.addHandler(handler)

    for handler in logger.handlers:
        if getattr(handler, _CONSOLE_HANDLER_MARKER, False):
            handler.setLevel(level)


def get_knowact_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{KNOWACT_LOGGER_NAME}.{name}")
