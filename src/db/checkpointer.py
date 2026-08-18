from __future__ import annotations

import psycopg
import structlog
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import get_config
from src.db.connection import get_async_pool, get_pool

logger = structlog.get_logger(__name__)

_tables_ready = False


def _ensure_checkpoint_tables() -> None:
    global _tables_ready
    if _tables_ready:
        return

    config = get_config()
    with psycopg.connect(config.postgres.connection_string, autocommit=True) as conn:
        PostgresSaver(conn).setup()

    _tables_ready = True
    logger.info("checkpointer_tables_ready")


def get_checkpointer() -> PostgresSaver:
    _ensure_checkpoint_tables()
    return PostgresSaver(get_pool())


async def get_async_checkpointer() -> AsyncPostgresSaver:
    _ensure_checkpoint_tables()
    return AsyncPostgresSaver(await get_async_pool())