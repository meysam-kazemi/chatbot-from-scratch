import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.language_models.fake_chat_models import (
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.tools import _safe_path, _workspace, write_file


class ToolCallingFakeModel(FakeMessagesListChatModel):
    def bind_tools(self, *args, **kwargs):
        return self


class ToolTest(unittest.TestCase):
    def test_workspace_paths_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "chatbot.ai.tools.settings.tool_workspace", directory
        ):
            workspace = _workspace(
                {"user_id": "user", "conversation_id": "conversation"}
            )
            self.assertEqual(
                _safe_path(workspace, "notes/result.txt"),
                Path(directory).resolve()
                / "user"
                / "conversation"
                / "notes"
                / "result.txt",
            )
            with self.assertRaises(ValueError):
                _safe_path(workspace, "../../secret.txt")


class ToolRuntimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_injects_conversation_workspace(self):
        model = ToolCallingFakeModel(
            responses=[
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "write_file",
                            "args": {"path": "result.txt", "content": "ok"},
                            "id": "call-1",
                            "type": "tool_call",
                        }
                    ],
                ),
                AIMessage(content="done"),
            ]
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "chatbot.ai.tools.settings.tool_workspace", directory
        ):
            chatbot = AgenticChatbot(model=model, tools=[write_file])
            answer = await chatbot.ainvoke(
                "Write the file",
                "conversation",
                context={
                    "user_id": "user",
                    "conversation_id": "conversation",
                    "db": None,
                },
            )

            self.assertEqual(answer, "done")
            self.assertEqual(
                (
                    Path(directory)
                    / "user"
                    / "conversation"
                    / "result.txt"
                ).read_text(),
                "ok",
            )


if __name__ == "__main__":
    unittest.main()
