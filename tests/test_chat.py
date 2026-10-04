import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from chatbot.ai.agent import AgenticChatbot


class ChatTest(unittest.IsolatedAsyncioTestCase):
    async def test_history_hides_intermediate_tool_messages(self):
        chatbot = object.__new__(AgenticChatbot)
        chatbot.agent = SimpleNamespace(
            aget_state=AsyncMock(
                return_value=SimpleNamespace(
                    values={
                        "messages": [
                            HumanMessage(content="Rename this conversation"),
                            AIMessage(
                                content="",
                                tool_calls=[
                                    {
                                        "name": "rename_conversation",
                                        "args": {"title": "New title"},
                                        "id": "call-1",
                                        "type": "tool_call",
                                    }
                                ],
                            ),
                            ToolMessage(content="Renamed", tool_call_id="call-1"),
                            AIMessage(content="The conversation was renamed."),
                        ]
                    }
                )
            )
        )

        messages = await chatbot.aget_messages("conversation-1")

        self.assertEqual(
            [message.content for message in messages],
            ["Rename this conversation", "The conversation was renamed."],
        )

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
