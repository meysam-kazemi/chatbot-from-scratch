import unittest
import uuid

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from chatbot.ai.agent import AgenticChatbot
from chatbot.ai.tracing import PostgresTracer


@tool
def echo(text: str) -> str:
    """Return text unchanged."""
    return text


class ToolCallingModel(FakeMessagesListChatModel):
    def bind_tools(self, *args, **kwargs):
        return self


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        pass

    def add(self, row):
        self.rows.append(row)

    async def commit(self):
        pass

    async def rollback(self):
        pass


class FakeSessionFactory:
    def __init__(self):
        self.rows = []

    def __call__(self):
        return FakeSession(self.rows)


class TracingTest(unittest.IsolatedAsyncioTestCase):
    async def test_agent_trace_contains_model_and_tool_runs(self):
        session_factory = FakeSessionFactory()
        tracer = PostgresTracer(session_factory, uuid.uuid4(), uuid.uuid4())
        chatbot = AgenticChatbot(
            model=ToolCallingModel(
                responses=[
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "echo",
                                "args": {"text": "hello"},
                                "id": "call-1",
                                "type": "tool_call",
                            }
                        ],
                    ),
                    AIMessage(content="hello"),
                ]
            ),
            tools=[echo],
        )

        self.assertEqual(
            await chatbot.ainvoke("Echo hello", callbacks=[tracer]),
            "hello",
        )
        await tracer.persist()

        payload = session_factory.rows[0].payload
        run_types = {
            run["run_type"]
            for run in payload["child_runs"]
            + [child for run in payload["child_runs"] for child in run["child_runs"]]
        }
        self.assertIn("llm", run_types)
        self.assertIn("tool", run_types)
        self.assertEqual(payload["inputs"]["messages"][0]["content"], "Echo hello")


if __name__ == "__main__":
    unittest.main()
