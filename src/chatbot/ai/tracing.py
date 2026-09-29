import logging
import uuid

from langchain_core.tracers.base import BaseTracer
from langchain_core.tracers.schemas import Run
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool


logger = logging.getLogger(__name__)


def _dump_run(run: Run) -> dict:
    payload = run.model_dump(
        mode="json",
        exclude={"ls_client", "parent_run"},
        fallback=str,
    )
    payload["child_runs"] = [_dump_run(child) for child in run.child_runs]
    return payload


class PostgresTracer(BaseTracer):
    run_inline = True

    def __init__(
        self,
        pool: AsyncConnectionPool,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> None:
        super().__init__()
        self.pool = pool
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.completed_runs: list[Run] = []

    def _persist_run(self, run: Run) -> None:
        self.completed_runs.append(run)

    async def persist(self) -> None:
        # ponytail: completed traces only; persist start events if crash traces matter.
        runs, self.completed_runs = self.completed_runs, []
        for run in runs:
            try:
                async with self.pool.connection() as connection:
                    await connection.execute(
                        """INSERT INTO traces (
                               id, user_id, conversation_id, name, run_type,
                               started_at, ended_at, payload
                           ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            run.id,
                            self.user_id,
                            self.conversation_id,
                            run.name,
                            run.run_type,
                            run.start_time,
                            run.end_time,
                            Jsonb(_dump_run(run)),
                        ),
                    )
            except Exception:
                logger.exception("trace_write_failed run_id=%s", run.id)
