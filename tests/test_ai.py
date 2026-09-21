import unittest
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.model import get_chat_model, settings


class AITest(unittest.TestCase):
    def test_agent_returns_last_message_and_rejects_blank_input(self):
        chatbot = AgenticChatbot(model=FakeListChatModel(responses=["Hello!"]))

        self.assertEqual(chatbot.invoke("Hi"), "Hello!")
        with self.assertRaises(ValueError):
            chatbot.invoke("   ")

    @patch("chatbot.ai.model.init_chat_model")
    def test_model_uses_settings(self, init_chat_model):
        with patch("chatbot.ai.model.settings.openai_api_key", "test-key"):
            get_chat_model()

        init_chat_model.assert_called_once_with(
            model=settings.ai_model,
            api_key="test-key",
            temperature=settings.ai_temperature,
            max_tokens=settings.ai_max_tokens,
            timeout=settings.ai_timeout,
            max_retries=settings.ai_max_retries,
        )


if __name__ == "__main__":
    unittest.main()
