"""
LangGraph SQLite checkpointer factory.

Uses AsyncSqliteSaver from langgraph-checkpoint-sqlite, which manages its own
tables (checkpoints, checkpoint_writes, checkpoint_blobs) inside the existing
ai_browser.db file.  Existing tables are never touched.

The checkpointer is an async context manager — we keep a module-level instance
that is initialised once during FastAPI lifespan startup and torn down on exit.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("graph.checkpointer")

_saver = None  # AsyncSqliteSaver instance, set during lifespan


def get_checkpointer():
    """Return the initialised AsyncSqliteSaver.  Must be called after init_checkpointer()."""
    if _saver is None:
        raise RuntimeError(
            "LangGraph checkpointer has not been initialised. "
            "Call await init_checkpointer() during FastAPI lifespan."
        )
    return _saver


async def init_checkpointer(db_path: str) -> None:
    """
    Initialise the AsyncSqliteSaver and create its schema tables.

    Call once from the FastAPI lifespan context manager.
    db_path: absolute filesystem path to ai_browser.db (not a SQLAlchemy URL).
    """
    global _saver
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    import aiosqlite

    # Strip SQLAlchemy URL prefix if passed
    path = db_path
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if path.startswith(prefix):
            path = path[len(prefix):]

    logger.info(f"Initialising LangGraph AsyncSqliteSaver with path: {path}")

    if path == ":memory:":
        conn = await aiosqlite.connect(":memory:")
    else:
        # Resolve relative paths from the backend directory
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), "..", "..", "..", path)
        path = os.path.normpath(path)
        conn = await aiosqlite.connect(path)

    saver = AsyncSqliteSaver(conn)
    await saver.setup()   # Creates langgraph checkpoint tables if not present
    _saver = saver
    logger.info("LangGraph checkpointer ready.")


async def close_checkpointer() -> None:
    """Close the SQLite connection.  Call during FastAPI lifespan shutdown."""
    global _saver
    if _saver is not None:
        try:
            await _saver.conn.close()
        except Exception as e:
            logger.warning(f"Error closing LangGraph checkpointer: {e}")
        finally:
            _saver = None
