import logging
import uuid

from langchain_core.tracers.base import BaseTracer
from langchain_core.tracers.schemas import Run

from chatbot.db.database import SessionFactory
from chatbot.db.models.trace import Trace


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
        session_factory: SessionFactory,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
    ) -> None:
        super().__init__()
        self.session_factory = session_factory
        self.user_id = user_id
        self.conversation_id = conversation_id
        self.completed_runs: list[Run] = []

    def _persist_run(self, run: Run) -> None:
        self.completed_runs.append(run)

    async def persist(self) -> None:
        # ponytail: completed traces only; persist start events if crash traces matter.
        runs, self.completed_runs = self.completed_runs, []
        for run in runs:
            async with self.session_factory() as session:
                try:
                    session.add(
                        Trace(
                            id=run.id,
                            user_id=self.user_id,
                            conversation_id=self.conversation_id,
                            name=run.name,
                            run_type=run.run_type,
                            started_at=run.start_time,
                            ended_at=run.end_time,
                            payload=_dump_run(run),
                        )
                    )
                    await session.commit()
                except Exception:
                    await session.rollback()
                    logger.exception("trace_write_failed run_id=%s", run.id)
