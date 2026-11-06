"""Add immutable task events and baseline existing rows without changing their IDs."""
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _timestamp(value):
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        # SQLite would otherwise reuse a deleted highest ID, merging unrelated histories.
        # Alembic copies every row, constraint and index; no existing Task is reset.
        with op.batch_alter_table("tasks", recreate="always",
                                  table_kwargs={"sqlite_autoincrement": True}):
            pass

    events = op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(16), nullable=False),
        sa.Column("before_state", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("after_state", sa.JSON(none_as_null=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('CREATED','UPDATED','COMPLETED','UNCOMPLETED','DELETED','BASELINE')",
            name="ck_task_events_type",
        ),
        sa.CheckConstraint(
            "(event_type IN ('CREATED','BASELINE') AND before_state IS NULL AND after_state IS NOT NULL) OR "
            "(event_type = 'DELETED' AND before_state IS NOT NULL AND after_state IS NULL) OR "
            "(event_type IN ('UPDATED','COMPLETED','UNCOMPLETED') "
            "AND before_state IS NOT NULL AND after_state IS NOT NULL)",
            name="ck_task_events_states",
        ),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_task_events_order", "task_events", ["occurred_at", "id"])
    op.create_index("ix_task_events_task_order", "task_events", ["task_id", "occurred_at", "id"])
    op.create_index("uq_task_events_baseline", "task_events", ["task_id"], unique=True,
                    sqlite_where=sa.text("event_type = 'BASELINE'"),
                    postgresql_where=sa.text("event_type = 'BASELINE'"))

    tasks = sa.table("tasks", sa.column("id", sa.Integer()), sa.column("title", sa.String()),
                     sa.column("description", sa.Text()), sa.column("scheduled_date", sa.Date()),
                     sa.column("is_completed", sa.Boolean()), sa.column("created_at", sa.DateTime()),
                     sa.column("updated_at", sa.DateTime()), sa.column("completed_at", sa.DateTime()))
    baseline_time = datetime.now(UTC)
    for task in connection.execute(sa.select(tasks).order_by(tasks.c.id)).mappings():
        state = dict(task)
        state["scheduled_date"] = state["scheduled_date"].isoformat()
        for field in ("created_at", "updated_at", "completed_at"):
            state[field] = _timestamp(state[field])
        connection.execute(events.insert().values(
            task_id=state["id"], event_type="BASELINE", before_state=None,
            after_state=state, occurred_at=baseline_time,
        ))

    if connection.dialect.name == "sqlite":
        for operation in ("UPDATE", "DELETE"):
            op.execute(sa.text(f"""CREATE TRIGGER task_events_no_{operation.lower()}
                BEFORE {operation} ON task_events BEGIN
                SELECT RAISE(ABORT, 'task_events are append-only'); END"""))
    elif connection.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION reject_task_event_change() RETURNS trigger
            LANGUAGE plpgsql AS $$ BEGIN
            RAISE EXCEPTION 'task_events are append-only'; END; $$""")
        op.execute("""CREATE TRIGGER task_events_append_only BEFORE UPDATE OR DELETE
            ON task_events FOR EACH ROW EXECUTE FUNCTION reject_task_event_change()""")


def downgrade():
    connection = op.get_bind()
    if connection.dialect.name == "sqlite":
        op.execute("DROP TRIGGER task_events_no_update")
        op.execute("DROP TRIGGER task_events_no_delete")
    elif connection.dialect.name == "postgresql":
        op.execute("DROP TRIGGER task_events_append_only ON task_events")
        op.execute("DROP FUNCTION reject_task_event_change()")
    op.drop_table("task_events")
    if connection.dialect.name == "sqlite":
        with op.batch_alter_table("tasks", recreate="always",
                                  table_kwargs={"sqlite_autoincrement": False}):
            pass
