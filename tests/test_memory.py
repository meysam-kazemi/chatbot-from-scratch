import unittest
import uuid
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
                "name": "save_memory", "args": {"content": "# Preferences\n- Reply in Persian."},
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

        document = "# Preferences\n- Reply in Persian."
        with patch.object(ToolCallingFakeModel, "_agenerate", capture), patch(
            "chatbot.repositories.memories.get_for_user",
            new=AsyncMock(side_effect=["", document, document]),
        ) as load, patch("chatbot.repositories.memories.save", new_callable=AsyncMock) as save:
            chatbot = AgenticChatbot(model=model, tools=[save_memory])
            await chatbot.ainvoke("Remember my language", "one", context=context)
            await chatbot.ainvoke("My language?", "two", context={**context, "conversation_id": "two"})
            save.assert_awaited_once_with(context["db"], uuid.UUID(user_id), document)
            self.assertEqual(load.await_count, 3)
            self.assertNotIn(document, captured[0][0].text)
            self.assertIn(document, captured[1][0].text)
            self.assertIn(document, captured[2][0].text)
            state = await chatbot.agent.aget_state({"configurable": {"thread_id": "two"}})
            self.assertTrue(all(m.type != "system" for m in state.values["messages"]))

    async def test_save_validates_before_opening_database(self):
        factory = AsyncMock()
        with self.assertRaises(ValueError):
            await memories.save(factory, uuid.uuid4(), "x" * 50_001)
        factory.assert_not_called()

    async def test_repository_replaces_whole_document_and_scopes_read_to_user(self):
        user_id = uuid.uuid4()
        document = "# About me\nPython developer\n\n# Preferences\n- Persian\n"
        session = AsyncMock()
        session.scalar.return_value = document
        session.__aenter__.return_value = session
        factory = lambda: session
        await memories.save(factory, user_id, document)
        statement = session.execute.call_args.args[0]
        self.assertEqual(statement.compile().params["user_id"], user_id)
        self.assertEqual(statement.compile().params["content"], document)
        self.assertNotIn("key", statement.compile().params)
        self.assertIn("ON CONFLICT (user_id) DO UPDATE", str(statement))
        session.commit.assert_awaited_once()
        self.assertEqual(await memories.get_for_user(factory, user_id), document)
        query = session.scalar.call_args.args[0]
        self.assertIn(user_id, query.compile().params.values())
        self.assertIn("WHERE user_memories.user_id =", str(query))
        self.assertEqual(list(query.selected_columns.keys()), ["content"])

    async def test_missing_memory_is_empty_and_document_can_be_cleared(self):
        session = AsyncMock()
        session.__aenter__.return_value = session
        session.scalar.return_value = None
        factory = lambda: session
        self.assertEqual(await memories.get_for_user(factory, uuid.uuid4()), "")
        await memories.save(factory, uuid.uuid4(), "")
        self.assertEqual(session.execute.call_args.args[0].compile().params["content"], "")
