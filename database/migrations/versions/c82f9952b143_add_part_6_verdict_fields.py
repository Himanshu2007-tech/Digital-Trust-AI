"""add_part_6_verdict_fields

Revision ID: c82f9952b143
Revises: b71e8841a021
Create Date: 2026-09-27 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c82f9952b143'
down_revision: Union[str, None] = 'b71e8841a021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    vr_cols = [c['name'] for c in inspector.get_columns('verification_results')]

    with op.batch_alter_table('verification_results', schema=None) as batch_op:
        if 'claim_id' not in vr_cols:
            batch_op.add_column(sa.Column('claim_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_verification_results_claim', 'claims', ['claim_id'], ['id'], ondelete='CASCADE')
            batch_op.create_index(op.f('ix_verification_results_claim_id'), ['claim_id'], unique=False)
        
        if 'verdict' not in vr_cols:
            batch_op.add_column(sa.Column('verdict', sa.String(length=50), nullable=False, server_default='UNVERIFIED'))
            batch_op.create_index(op.f('ix_verification_results_verdict'), ['verdict'], unique=False)

        if 'confidence' not in vr_cols:
            batch_op.add_column(sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'))

        if 'explanation' not in vr_cols:
            batch_op.add_column(sa.Column('explanation', sa.Text(), nullable=False, server_default=''))

        if 'supporting_evidence_ids' not in vr_cols:
            batch_op.add_column(sa.Column('supporting_evidence_ids', sa.JSON(), nullable=True))

        if 'contradicting_evidence_ids' not in vr_cols:
            batch_op.add_column(sa.Column('contradicting_evidence_ids', sa.JSON(), nullable=True))

        if 'contextual_evidence_ids' not in vr_cols:
            batch_op.add_column(sa.Column('contextual_evidence_ids', sa.JSON(), nullable=True))

        if 'limitations' not in vr_cols:
            batch_op.add_column(sa.Column('limitations', sa.JSON(), nullable=True))

        if 'generated_at' not in vr_cols:
            batch_op.add_column(sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True))

        if 'methodology_version' not in vr_cols:
            batch_op.add_column(sa.Column('methodology_version', sa.String(length=50), nullable=False, server_default='truthlens-v1.0'))

        # Make request_id nullable so claim results without request can exist
        batch_op.alter_column('request_id',
                   existing_type=sa.Integer(),
                   nullable=True)
        try:
            batch_op.drop_index('ix_verification_results_request_id')
            batch_op.create_index('ix_verification_results_request_id', ['request_id'], unique=False)
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table('verification_results', schema=None) as batch_op:
        batch_op.drop_column('methodology_version')
        batch_op.drop_column('generated_at')
        batch_op.drop_column('limitations')
        batch_op.drop_column('contextual_evidence_ids')
        batch_op.drop_column('contradicting_evidence_ids')
        batch_op.drop_column('supporting_evidence_ids')
        batch_op.drop_column('explanation')
        batch_op.drop_column('confidence')
        batch_op.drop_index(op.f('ix_verification_results_verdict'))
        batch_op.drop_column('verdict')
        batch_op.drop_index(op.f('ix_verification_results_claim_id'))
        batch_op.drop_column('claim_id')
