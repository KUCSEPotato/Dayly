from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session


@contextmanager
def write_transaction(session: Session):
    """Serialize writers before reading: snapshots and XP share the task transaction discipline."""
    try:
        dialect = session.get_bind().dialect.name
        if dialect == "sqlite":
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        elif dialect == "postgresql":
            session.execute(text("SELECT pg_advisory_xact_lock(4281021)"))
        yield
        session.commit()
    except Exception:
        session.rollback()
        raise
