import logging
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Response

from chatbot.api.request_logging import log_request
from chatbot.logging import configure_logging


class LoggingTest(unittest.TestCase):
    @patch("chatbot.logging.logging.basicConfig")
    def test_logging_uses_configured_level(self, basic_config):
        with patch("chatbot.logging.settings.log_level", "WARNING"):
            configure_logging()

        basic_config.assert_called_once_with(
            level="WARNING",
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )

    def test_application_logger_inherits_root_level(self):
        self.assertIsInstance(logging.getLogger("chatbot"), logging.Logger)


class RequestLoggingTest(unittest.IsolatedAsyncioTestCase):
    async def test_request_log_contains_safe_metadata(self):
        request = SimpleNamespace(
            method="POST",
            url=SimpleNamespace(path="/api/v1/chat/conversations"),
        )

        async def call_next(_request):
            return Response(status_code=201)

        with self.assertLogs("chatbot.api.request_logging", "INFO") as logs:
            response = await log_request(request, call_next)

        self.assertIn("X-Request-ID", response.headers)
        self.assertIn("method=POST", logs.output[0])
        self.assertIn("status=201", logs.output[0])
        self.assertNotIn("Authorization", logs.output[0])


if __name__ == "__main__":
    unittest.main()
