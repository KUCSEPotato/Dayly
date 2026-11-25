"""Add reusable tags and an optional event change reason; keep historical JSON untouched."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("normalized_name", sa.String(90), nullable=False, unique=True),
        sa.Column("color", sa.String(7), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(name)) BETWEEN 1 AND 30", name="ck_tags_name_length"),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    # ADD COLUMN preserves the existing append-only triggers and all stored states.
    op.add_column("task_events", sa.Column("change_reason", sa.String(32), nullable=True))


def downgrade():
    op.drop_column("task_events", "change_reason")
    op.drop_table("task_tags")
    op.drop_table("tags")
