import logging
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
