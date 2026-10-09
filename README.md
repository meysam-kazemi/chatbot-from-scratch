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
