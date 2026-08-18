from __future__ import annotations

from typing import Optional

import psycopg
from psycopg_pool import AsyncConnectionPool, ConnectionPool

from src.config import get_config

_pool: Optional[ConnectionPool] = None
_async_pool: Optional[AsyncConnectionPool] = None


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        config = get_config()
        pool = ConnectionPool(
            config.postgres.connection_string,
            min_size=2,
            max_size=10,
            timeout=config.postgres.pool_timeout_seconds,
            open=False,
        )
        pool.open(wait=False)
        _pool = pool
    return _pool


def get_connection(timeout: float | None = None):
    return get_pool().getconn(timeout=timeout)


def put_connection(conn):
    get_pool().putconn(conn)


async def get_async_pool() -> AsyncConnectionPool:
    global _async_pool
    if _async_pool is None:
        config = get_config()
        pool = AsyncConnectionPool(
            config.postgres.connection_string,
            min_size=1,
            max_size=10,
            timeout=config.postgres.pool_timeout_seconds,
            open=False,
        )
        await pool.open(wait=False)
        _async_pool = pool
    return _async_pool


async def close_async_pool():
    global _async_pool
    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None


def close_pools():
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None