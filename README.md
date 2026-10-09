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

Apply `uv run alembic upgrade head` to create `user_memories`. The assistant's
`save_memory(key, content)` tool stores facts in PostgreSQL for the authenticated
user. Reusing a key replaces its previous value. Keys allow 100 characters and
values allow 4,000 characters. Memory survives restarts and conversation deletion,
and is shared across that user's conversations, never across users.

All saved facts are loaded into the system context before each model call,
including after tools run. They are not copied into conversation checkpoints.
As memory grows, all entries consume model context; no retrieval filter or
automatic pruning is applied.

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
