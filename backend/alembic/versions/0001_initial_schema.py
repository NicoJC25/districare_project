"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emergencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("simulated_location", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ambulance_nodes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("simulated_location", sa.String(length=120), nullable=False),
        sa.Column("operational_load", sa.Integer(), nullable=False),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ambulance_nodes_code"),
    )
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("emergency_id", sa.String(length=36), nullable=False),
        sa.Column("ambulance_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reassignment_reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["ambulance_id"], ["ambulance_nodes.id"]),
        sa.ForeignKeyConstraint(["emergency_id"], ["emergencies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assignments_ambulance_id", "assignments", ["ambulance_id"])
    op.create_index("ix_assignments_emergency_id", "assignments", ["emergency_id"])
    op.create_index(
        "uq_active_confirmed_assignment_per_emergency",
        "assignments",
        ["emergency_id"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE AND state = 'CONFIRMADA'"),
    )
    op.create_table(
        "ai_recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("emergency_id", sa.String(length=36), nullable=False),
        sa.Column("recommended_ambulance_id", sa.String(length=36), nullable=True),
        sa.Column("calculated_priority", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Float(), nullable=False),
        sa.Column("criteria", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["emergency_id"], ["emergencies.id"]),
        sa.ForeignKeyConstraint(["recommended_ambulance_id"], ["ambulance_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_recommendations_emergency_id", "ai_recommendations", ["emergency_id"])
    op.create_table(
        "node_failures",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ambulance_id", sa.String(length=36), nullable=False),
        sa.Column("failure_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("failed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("recovery_state", sa.String(length=40), nullable=False),
        sa.Column("recovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ambulance_id"], ["ambulance_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_node_failures_ambulance_id", "node_failures", ["ambulance_id"])
    op.create_table(
        "system_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("emergency_id", sa.String(length=36), nullable=True),
        sa.Column("ambulance_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("event_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ambulance_id"], ["ambulance_nodes.id"]),
        sa.ForeignKeyConstraint(["emergency_id"], ["emergencies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_events_ambulance_id", "system_events", ["ambulance_id"])
    op.create_index("ix_system_events_emergency_id", "system_events", ["emergency_id"])
    op.create_index("ix_system_events_event_type", "system_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("system_events")
    op.drop_table("node_failures")
    op.drop_table("ai_recommendations")
    op.drop_index("uq_active_confirmed_assignment_per_emergency", table_name="assignments")
    op.drop_table("assignments")
    op.drop_table("ambulance_nodes")
    op.drop_table("emergencies")
