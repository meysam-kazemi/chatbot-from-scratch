import unittest

from langchain_core.language_models.fake_chat_models import FakeListChatModel

from chatbot.ai.agent import AgenticChatbot


class ChatTest(unittest.IsolatedAsyncioTestCase):
    async def test_langgraph_is_the_message_store(self):
        chatbot = AgenticChatbot(
            model=FakeListChatModel(responses=["Hello!", "Again!"])
        )

        await chatbot.ainvoke("Hi", "conversation-1")
        await chatbot.ainvoke("One more", "conversation-1")

        messages = await chatbot.aget_messages("conversation-1")
        self.assertEqual(
            [message.content for message in messages],
            ["Hi", "Hello!", "One more", "Again!"],
        )

        await chatbot.adelete_conversation("conversation-1")
        self.assertEqual(await chatbot.aget_messages("conversation-1"), [])


if __name__ == "__main__":
    unittest.main()
