import io
import logging
import unittest

from backend.knowact.logging_config import (
    KNOWACT_LOGGER_NAME,
    _CONSOLE_HANDLER_MARKER,
    configure_knowact_logging,
    get_knowact_logger,
)


class KnowActLoggingConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self._logger = logging.getLogger(KNOWACT_LOGGER_NAME)
        self._original_handlers = list(self._logger.handlers)
        self._original_level = self._logger.level
        self._original_propagate = self._logger.propagate
        self._logger.handlers = [
            handler
            for handler in self._logger.handlers
            if not getattr(handler, _CONSOLE_HANDLER_MARKER, False)
        ]

    def tearDown(self) -> None:
        self._logger.handlers = self._original_handlers
        self._logger.setLevel(self._original_level)
        self._logger.propagate = self._original_propagate

    def test_console_logs_use_readable_uvicorn_style_prefix(self):
        stream = io.StringIO()
        configure_knowact_logging(stream=stream, use_colors=False)

        get_knowact_logger("authoring.map_authoring").info(
            "Candidate map reviewed graph loaded run_id=%s graph_version=%s nodes=%d",
            "map_run_001",
            "v0.1",
            80,
        )

        output = stream.getvalue()
        self.assertIn("knowact.authoring.map_authoring: Candidate map reviewed graph loaded", output)
        self.assertNotIn("INFO:knowact.authoring.map_authoring", output)

    def test_configure_logging_is_idempotent(self):
        stream = io.StringIO()

        configure_knowact_logging(stream=stream, use_colors=False)
        configure_knowact_logging(stream=stream, use_colors=False)

        console_handlers = [
            handler
            for handler in self._logger.handlers
            if getattr(handler, _CONSOLE_HANDLER_MARKER, False)
        ]
        self.assertEqual(1, len(console_handlers))


if __name__ == "__main__":
    unittest.main()
