import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event
from backend.app.config import settings
from backend.app.database.models import Base

# Ensure SQLite URL is formatted for async
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite:///"):
    db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True,
    connect_args={"check_same_thread": False}
)

# Enable SQLite WAL mode and foreign keys on connect
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def migrate_approval_requests(sync_conn):
            from sqlalchemy import text
            res = sync_conn.execute(text("PRAGMA table_info(approval_requests)"))
            columns = [row[1] for row in res.fetchall()]
            if "step_number" not in columns:
                sync_conn.execute(text("ALTER TABLE approval_requests ADD COLUMN step_number INTEGER"))
            if "session_checkpoint_json" not in columns:
                sync_conn.execute(text("ALTER TABLE approval_requests ADD COLUMN session_checkpoint_json TEXT"))
            if "resolved_at" not in columns:
                sync_conn.execute(text("ALTER TABLE approval_requests ADD COLUMN resolved_at REAL"))
            if "error" not in columns:
                sync_conn.execute(text("ALTER TABLE approval_requests ADD COLUMN error TEXT"))

        def migrate_desktop_audit_logs(sync_conn):
            from sqlalchemy import text
            res = sync_conn.execute(text("PRAGMA table_info(desktop_audit_logs)"))
            columns = [row[1] for row in res.fetchall()]
            if "action_type" not in columns:
                sync_conn.execute(text("ALTER TABLE desktop_audit_logs ADD COLUMN action_type VARCHAR(64)"))
            if "target" not in columns:
                sync_conn.execute(text("ALTER TABLE desktop_audit_logs ADD COLUMN target VARCHAR(255)"))
            if "status" not in columns:
                sync_conn.execute(text("ALTER TABLE desktop_audit_logs ADD COLUMN status VARCHAR(32)"))
            if "duration_ms" not in columns:
                sync_conn.execute(text("ALTER TABLE desktop_audit_logs ADD COLUMN duration_ms REAL"))

        await conn.run_sync(migrate_approval_requests)
        await conn.run_sync(migrate_desktop_audit_logs)

        def migrate_tasks_langgraph(sync_conn):
            """Add LangGraph thread/checkpoint columns to tasks table (safe, idempotent)."""
            from sqlalchemy import text
            res = sync_conn.execute(text("PRAGMA table_info(tasks)"))
            columns = [row[1] for row in res.fetchall()]
            if "graph_thread_id" not in columns:
                sync_conn.execute(text(
                    "ALTER TABLE tasks ADD COLUMN graph_thread_id VARCHAR(128)"
                ))
            if "lg_checkpoint_id" not in columns:
                sync_conn.execute(text(
                    "ALTER TABLE tasks ADD COLUMN lg_checkpoint_id VARCHAR(128)"
                ))

        await conn.run_sync(migrate_tasks_langgraph)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
