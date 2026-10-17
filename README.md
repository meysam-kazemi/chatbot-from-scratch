# chatbot-from-scratch

## Database migrations

Application tables are managed by Alembic. Start PostgreSQL and apply all
migrations before starting the application:

```bash
docker compose up -d postgres
uv run alembic upgrade head
uv run python -m chatbot.main
```

For a database that already had the application tables before Alembic was
introduced, mark the baseline as applied once instead of recreating it:

```bash
uv run alembic stamp 20261003_01
```

Create future migrations from the SQLAlchemy models with:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

Review the generated `upgrade()` and `downgrade()` functions, then run
`uv run alembic upgrade head`. Application queries use async SQLAlchemy
sessions, and the models in `src/chatbot/db/models/` are the source for
Alembic autogeneration.

## Long-term memory

Apply `uv run alembic upgrade head` to create or migrate `user_memories`.
Each user has one PostgreSQL `TEXT` document, like a private `MEMORY.md`, with
free-form Markdown containing preferences and useful personal information:

```markdown
# About me
I am a Python developer working on an agentic chatbot.

# Preferences
- Reply in Persian.
- Explain concepts with small code examples.
```

Before each production chat turn, a separate structured LLM call extracts durable
facts and preferences from the latest user message, using recent conversation
for context. It returns a validated `MemoryUpdate`: a complete revised Markdown
document, or `null` for no change. Changed documents are committed to PostgreSQL
before the assistant answers. This adds one LLM call per turn; the default uses
`AI_MODEL` and its timeout/token settings. Extraction or persistence failures
fail the turn rather than claiming that information was saved. Memory extraction
output is excluded from chat streaming events.

The assistant's `save_memory(content)` tool also replaces the complete document.
It reads the existing document from context and supplies the revised text,
preserving unrelated information and correcting outdated facts. Empty content
clears the document; writes allow up to 50,000 characters. There are no memory
keys or memory search. The document is stored in the database, not on disk.
Existing key-value memories are migrated into Markdown sections without losing
facts. Memory survives restarts and conversation deletion and is private to
each user across their conversations.

The full text is loaded before every model call, including after tools run,
and is not copied into conversation checkpoints. All of it consumes model
context; no retrieval filter or automatic pruning is applied.

## Structured LLM output

Titles use a validated `ConversationTitle` schema with provider JSON Schema
output. Automatic memory extraction uses the same mechanism with `MemoryUpdate`.
Normal chat replies remain streamed Markdown. For programmatic agents, pass a
Pydantic model (or LangChain response strategy) as `response_format`:

```python
from pydantic import BaseModel
from chatbot.ai.agent import AgenticChatbot

class Answer(BaseModel):
    summary: str
    next_steps: list[str]

agent = AgenticChatbot(response_format=Answer)
result = await agent.ainvoke("Explain how this project stores memory")
print(result.summary)
```

`invoke` and `ainvoke` return the validated structured response when configured.
LangChain selects provider-native output or a tool strategy according to model
capabilities. Structured streaming buffers the result until validation succeeds,
then emits JSON as a single `delta` and the final `answer`, avoiding partial JSON.
When injecting your own chat `model`, also pass `memory_model` to enable automatic
memory extraction; it must support `with_structured_output`. Both memory paths
require runtime context containing `user_id`, `conversation_id`, and the database
session factory. The API supplies this context automatically.

## Streaming and tool progress

The chat UI uses `POST /api/v1/chat/conversations/{id}/messages/stream` with
Bearer authentication and a JSON body: `{"message": "Hello"}`. The response is
Server-Sent Events consumed through streaming `fetch`, so the usual token refresh
works before streaming begins. The original JSON message endpoint is still available.

Each frame has an `event:` field and JSON `data:` containing the same event name:

- `message_start`: a model response begins; reset the current text buffer.
- `delta`: append `text` to that buffer.
- `tool_start` / `tool_end`: show tool `name` and correlate by `id`.
  End events report `status` (`ok` or `error` when the tool returns an error-status message).
  Tool arguments and results are excluded from progress events.
- `answer`: the authoritative final `content`, also available from conversation history.
- `done`: the turn completed, with an optional generated `title`.
- `error`: a safe error `message`; the client should reload history before retrying.

Tool progress reports start and completion rather than a percentage. Text from
an intermediate model call is replaced when the next model response begins.
The UI prevents conversation switching and duplicate sends during a turn.
A disconnected client can leave a partial checkpoint; reload history before retrying.

Run Python tests with `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`.
Run the streaming parser tests with `node --test tests/test_streaming_ui.cjs`.
