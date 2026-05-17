"""assignment confirmation fields

Revision ID: 0002_assignment_confirm
Revises: 0001_initial_schema
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_assignment_confirm"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("emergencies") as batch_op:
        batch_op.add_column(sa.Column("assigned_ambulance_id", sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            "fk_emergencies_assigned_ambulance_id_ambulance_nodes",
            "ambulance_nodes",
            ["assigned_ambulance_id"],
            ["id"],
        )
        batch_op.create_index("ix_emergencies_assigned_ambulance_id", ["assigned_ambulance_id"])
    op.create_index(
        "uq_active_confirmed_assignment_per_ambulance",
        "assignments",
        ["ambulance_id"],
        unique=True,
        postgresql_where=sa.text("active IS TRUE AND state = 'CONFIRMADA'"),
        sqlite_where=sa.text("active IS TRUE AND state = 'CONFIRMADA'"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_confirmed_assignment_per_ambulance", table_name="assignments")
    with op.batch_alter_table("emergencies") as batch_op:
        batch_op.drop_index("ix_emergencies_assigned_ambulance_id")
        batch_op.drop_constraint("fk_emergencies_assigned_ambulance_id_ambulance_nodes", type_="foreignkey")
        batch_op.drop_column("assigned_ambulance_id")
