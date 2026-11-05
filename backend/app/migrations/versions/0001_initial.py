"""The planner's tables

Revision ID: 0001
Revises:
Create Date: 2026-11-05
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("hub_id", sa.Integer, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("role", sa.Enum("PARENT", "CHILD", name="role"), nullable=False),
        sa.Column("color", sa.String(7)),
        sa.Column("language", sa.String(2)),
        sa.Column("is_active", sa.Boolean, nullable=False),
        sa.UniqueConstraint("hub_id", name="uq_people_hub_id"),
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("credential", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(500)),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("last_success_at", sa.DateTime),
        sa.Column("last_error", sa.String(40)),
        sa.Column("last_error_at", sa.DateTime),
    )
    op.create_table(
        "calendars",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "source_id",
            sa.Integer,
            sa.ForeignKey("sources.id", ondelete="CASCADE", name="fk_calendars_source_id_sources"),
            nullable=False,
        ),
        sa.Column("remote_id", sa.String(500), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("ctag", sa.String(200)),
        sa.Column(
            "person_id", sa.Integer, sa.ForeignKey("people.id", ondelete="SET NULL", name="fk_calendars_person_id_people")
        ),
        sa.Column("color", sa.String(7)),
        sa.Column("visible", sa.Boolean, nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.UniqueConstraint("source_id", "remote_id", name="uq_calendars_source_id"),
    )
    op.create_table(
        "series",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "calendar_id",
            sa.Integer,
            sa.ForeignKey("calendars.id", ondelete="CASCADE", name="fk_series_calendar_id_calendars"),
            nullable=False,
        ),
        sa.Column("uid", sa.String(500), nullable=False),
        sa.Column("ics", sa.Text, nullable=False),
        sa.Column("first_start", sa.DateTime, nullable=False),
        sa.Column("last_end", sa.DateTime),
        sa.Column("href", sa.String(500)),
        sa.Column("etag", sa.String(200)),
        sa.UniqueConstraint("calendar_id", "uid", name="uq_series_calendar_id"),
    )
    op.create_index("ix_series_calendar_start", "series", ["calendar_id", "first_start"])
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("family_color", sa.String(7), nullable=False),
    )


def downgrade() -> None:
    for table in ("settings", "series", "calendars", "sources", "people"):
        op.drop_table(table)
