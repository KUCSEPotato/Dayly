"""Persist immutable retrospectives, history coverage and an idempotent XP ledger."""
from datetime import UTC, datetime

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    coverage = op.create_table(
        "history_coverage", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_history_coverage_singleton"),
    )
    # Conservative coverage: do not invent empty days before the first known event.
    events = sa.table("task_events", sa.column("occurred_at", sa.DateTime(timezone=True)))
    earliest = op.get_bind().scalar(sa.select(sa.func.min(events.c.occurred_at)))
    op.bulk_insert(coverage, [{"id": 1, "started_at": earliest or datetime.now(UTC)}])
    op.create_table(
        "retrospective_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("total", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Integer(), nullable=True),
        sa.Column("incomplete", sa.Integer(), nullable=True),
        sa.Column("completion_rate", sa.Float(), nullable=True),
        sa.Column("xp_total", sa.Integer(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.UniqueConstraint("kind", "period_start", "period_end", name="uq_retrospective_period"),
        sa.CheckConstraint("kind IN ('daily','weekly','monthly')", name="ck_retrospective_kind"),
        sa.CheckConstraint("period_start < period_end", name="ck_retrospective_period"),
        sa.CheckConstraint("status IN ('ready','no_activity','partial','unavailable')", name="ck_retrospective_status"),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "experience_grants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("dedup_key", sa.String(120), nullable=False, unique=True),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("earned_date", sa.Date(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("policy_version", sa.String(24), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_experience_amount"),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_experience_earned_date", "experience_grants", ["earned_date", "id"])
    for table in ("retrospective_snapshots", "experience_grants"):
        if op.get_bind().dialect.name == "sqlite":
            for operation in ("UPDATE", "DELETE"):
                op.execute(f"""CREATE TRIGGER {table}_no_{operation.lower()}
                    BEFORE {operation} ON {table} BEGIN
                    SELECT RAISE(ABORT, '{table} are immutable'); END""")
        elif op.get_bind().dialect.name == "postgresql":
            op.execute(f"""CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION reject_task_event_change()""")


def downgrade():
    for table in ("experience_grants", "retrospective_snapshots"):
        if op.get_bind().dialect.name == "sqlite":
            for operation in ("update", "delete"):
                op.execute(f"DROP TRIGGER {table}_no_{operation}")
        elif op.get_bind().dialect.name == "postgresql":
            op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
        op.drop_table(table)
    op.drop_table("history_coverage")
