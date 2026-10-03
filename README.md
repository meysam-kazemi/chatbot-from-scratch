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
