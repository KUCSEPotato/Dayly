"""Create tasks and their scheduled-date index."""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_tasks_title_not_blank"),
        sa.CheckConstraint(
            "(is_completed AND completed_at IS NOT NULL) OR "
            "(NOT is_completed AND completed_at IS NULL)",
            name="ck_tasks_completion_consistent",
        ),
    )
    op.create_index("ix_tasks_scheduled_date", "tasks", ["scheduled_date"])


def downgrade():
    op.drop_index("ix_tasks_scheduled_date", table_name="tasks")
    op.drop_table("tasks")
