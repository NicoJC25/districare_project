"""recommendation trace fields

Revision ID: 0003_recommend_trace
Revises: 0002_assignment_confirm
Create Date: 2026-05-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_recommend_trace"
down_revision = "0002_assignment_confirm"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ai_recommendations") as batch_op:
        batch_op.add_column(sa.Column("decision_reason", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("candidates_count", sa.Integer(), nullable=False, server_default="0"))

    op.execute(
        """
        UPDATE ai_recommendations
        SET decision_reason = CASE
            WHEN recommended_ambulance_id IS NULL
            THEN 'No hay ambulancias disponibles o recuperadas para recomendar.'
            ELSE 'Recomendacion calculada por ranking heuristico.'
        END
        WHERE decision_reason IS NULL
        """
    )

    with op.batch_alter_table("ai_recommendations") as batch_op:
        batch_op.alter_column("decision_reason", existing_type=sa.String(length=500), nullable=False)
        batch_op.alter_column("candidates_count", server_default=None)

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.add_column(sa.Column("recommendation_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("recommended_ambulance_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("assignment_reason", sa.String(length=500), nullable=True))
        batch_op.create_foreign_key(
            "fk_assignments_recommendation_id_ai_recommendations",
            "ai_recommendations",
            ["recommendation_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_assignments_recommended_ambulance_id_ambulance_nodes",
            "ambulance_nodes",
            ["recommended_ambulance_id"],
            ["id"],
        )
        batch_op.create_index("ix_assignments_recommendation_id", ["recommendation_id"])
        batch_op.create_index("ix_assignments_recommended_ambulance_id", ["recommended_ambulance_id"])


def downgrade() -> None:
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_index("ix_assignments_recommended_ambulance_id")
        batch_op.drop_index("ix_assignments_recommendation_id")
        batch_op.drop_constraint("fk_assignments_recommended_ambulance_id_ambulance_nodes", type_="foreignkey")
        batch_op.drop_constraint("fk_assignments_recommendation_id_ai_recommendations", type_="foreignkey")
        batch_op.drop_column("assignment_reason")
        batch_op.drop_column("recommended_ambulance_id")
        batch_op.drop_column("recommendation_id")

    with op.batch_alter_table("ai_recommendations") as batch_op:
        batch_op.drop_column("candidates_count")
        batch_op.drop_column("decision_reason")
