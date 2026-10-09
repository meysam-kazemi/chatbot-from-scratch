import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import AIMessage
from langchain.tools import tool

from chatbot.ai.agent import AgenticChatbot
from chatbot.api.routes.chat import router
from chatbot.api.dependencies import get_chatbot, get_current_user, get_title_generator
from test_tools import ToolCallingFakeModel


class AgentStreamingTest(unittest.IsolatedAsyncioTestCase):
    async def test_deltas_and_checkpointed_final_answer(self):
        chatbot = AgenticChatbot(model=FakeListChatModel(responses=["Hello!"]))
        events = [event async for event in chatbot.astream("Hi", "stream")]
        self.assertEqual("".join(e["text"] for e in events if e["event"] == "delta"), "Hello!")
        self.assertEqual(events[-1], {"event": "answer", "content": "Hello!"})
        self.assertEqual([m.content for m in await chatbot.aget_messages("stream")], ["Hi", "Hello!"])
        with self.assertRaises(ValueError):
            _ = [e async for e in chatbot.astream(" ")]

    async def test_tool_progress_excludes_arguments_and_output(self):
        @tool
        def lookup(secret: str) -> str:
            """Look up a fact."""
            return "private tool output"

        model = ToolCallingFakeModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "lookup", "args": {"secret": "private input"},
                "id": "call-1", "type": "tool_call",
            }]), AIMessage(content="Done"),
        ])
        chatbot = AgenticChatbot(model=model, tools=[lookup])
        events = [event async for event in chatbot.astream("Look up something", "tools")]
        progress = [e for e in events if e["event"].startswith("tool_")]
        self.assertEqual([e["event"] for e in progress], ["tool_start", "tool_end"])
        self.assertEqual(progress[0]["id"], progress[1]["id"])
        self.assertNotIn("private", str(events))
        self.assertEqual(events[-1]["content"], "Done")


class StreamingAPITest(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.state.db = object()
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.conversation = SimpleNamespace(title=None)
        self.chatbot = AgenticChatbot(model=FakeListChatModel(responses=["Hi ✓"]))
        self.title = SimpleNamespace(ainvoke=AsyncMock(return_value="Greeting"))
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_chatbot] = lambda: self.chatbot
        self.app.dependency_overrides[get_title_generator] = lambda: self.title
        self.url = f"/chat/conversations/{uuid.uuid4()}/messages/stream"

    def test_stream_and_best_effort_title(self):
        self.title.ainvoke.side_effect = RuntimeError("provider secret")
        with patch("chatbot.api.routes.chat.owned_conversation", AsyncMock(return_value=self.conversation)), patch(
            "chatbot.ai.long_term_memory.memories.list_for_user", AsyncMock(return_value=[])
        ), patch("chatbot.api.routes.chat.conversations.touch", new_callable=AsyncMock) as touch, patch(
            "chatbot.api.routes.chat.PostgresTracer.persist", new_callable=AsyncMock
        ) as persist:
            with self.assertLogs("chatbot.api.routes.chat", level="ERROR"):
                response = TestClient(self.app).post(self.url, json={"message": "Hello"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/event-stream", response.headers["content-type"])
            self.assertIn("event: delta", response.text)
            self.assertIn("event: answer", response.text)
            self.assertIn("event: done", response.text)
            self.assertNotIn("provider secret", response.text)
            touch.assert_awaited_once()
            persist.assert_awaited_once()

    def test_failure_is_generic_and_traces_persist(self):
        async def broken(*args, **kwargs):
            yield {"event": "delta", "text": "Partial"}
            raise RuntimeError("database password")
        self.chatbot.astream = broken
        with patch("chatbot.api.routes.chat.owned_conversation", AsyncMock(return_value=self.conversation)), patch(
            "chatbot.api.routes.chat.PostgresTracer.persist", new_callable=AsyncMock
        ) as persist:
            with self.assertLogs("chatbot.api.routes.chat", level="ERROR"):
                response = TestClient(self.app).post(self.url, json={"message": "Hello"})
            self.assertIn("event: error", response.text)
            self.assertNotIn("event: done", response.text)
            self.assertNotIn("database password", response.text)
            persist.assert_awaited_once()

    def test_authentication_required(self):
        self.app.dependency_overrides.pop(get_current_user)
        response = TestClient(self.app).post(self.url, json={"message": "Hello"})
        self.assertEqual(response.status_code, 401)

    def test_missing_conversation_is_rejected_before_streaming(self):
        with patch("chatbot.api.routes.chat.conversations.get_for_user", AsyncMock(return_value=None)):
            response = TestClient(self.app).post(self.url, json={"message": "Hello"})
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("text/event-stream", response.headers["content-type"])
