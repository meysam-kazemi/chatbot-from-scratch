import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.tools import save_memory
from chatbot.repositories import memories
from test_tools import ToolCallingFakeModel


class MemoryTest(unittest.IsolatedAsyncioTestCase):
    async def test_save_tool_and_refresh_on_every_model_call(self):
        user_id = str(uuid.uuid4())
        context = {"user_id": user_id, "conversation_id": "one", "db": object()}
        model = ToolCallingFakeModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "save_memory", "args": {"key": "language", "content": "Persian"},
                "id": "save-1", "type": "tool_call",
            }]),
            AIMessage(content="Remembered"),
            AIMessage(content="Persian"),
        ])
        captured = []
        original = ToolCallingFakeModel._agenerate

        async def capture(instance, messages, **kwargs):
            captured.append(messages)
            return await original(instance, messages, **kwargs)

        entry = SimpleNamespace(key="language", content="Persian")
        with patch.object(ToolCallingFakeModel, "_agenerate", capture), patch(
            "chatbot.repositories.memories.list_for_user",
            new=AsyncMock(side_effect=[[], [entry], [entry]]),
        ) as load, patch("chatbot.repositories.memories.save", new_callable=AsyncMock) as save:
            chatbot = AgenticChatbot(model=model, tools=[save_memory])
            await chatbot.ainvoke("Remember my language", "one", context=context)
            await chatbot.ainvoke("My language?", "two", context={**context, "conversation_id": "two"})
            save.assert_awaited_once_with(context["db"], uuid.UUID(user_id), "language", "Persian")
            self.assertEqual(load.await_count, 3)
            self.assertNotIn('"language": "Persian"', str(captured[0][0].content))
            self.assertIn('"language": "Persian"', str(captured[1][0].content))
            self.assertIn('"language": "Persian"', str(captured[2][0].content))
            state = await chatbot.agent.aget_state({"configurable": {"thread_id": "two"}})
            self.assertTrue(all(m.type != "system" for m in state.values["messages"]))

    async def test_save_validates_before_opening_database(self):
        factory = AsyncMock()
        for key, content in [(" ", "fact"), ("k" * 101, "fact"), ("key", ""), ("key", "x" * 4001)]:
            with self.assertRaises(ValueError):
                await memories.save(factory, uuid.uuid4(), key, content)
        factory.assert_not_called()

    async def test_repository_scopes_read_and_upsert_to_user(self):
        user_id = uuid.uuid4()
        session = AsyncMock()
        session.scalars.return_value = []
        session.__aenter__.return_value = session
        factory = lambda: session
        await memories.save(factory, user_id, " language ", " Persian ")
        statement = session.execute.call_args.args[0]
        self.assertEqual(statement.compile().params["user_id"], user_id)
        self.assertEqual(statement.compile().params["key"], "language")
        self.assertIn("ON CONFLICT (user_id, key) DO UPDATE", str(statement))
        session.commit.assert_awaited_once()
        await memories.list_for_user(factory, user_id)
        query = session.scalars.call_args.args[0]
        self.assertIn(user_id, query.compile().params.values())
        self.assertIn("WHERE user_memories.user_id =", str(query))
