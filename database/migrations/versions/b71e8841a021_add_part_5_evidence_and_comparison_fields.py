"""add_part_5_evidence_and_comparison_fields

Revision ID: b71e8841a021
Revises: 3a3de1f1563e
Create Date: 2026-09-16 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b71e8841a021'
down_revision: Union[str, None] = '3a3de1f1563e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # 1. Batch alter evidence table
    ev_cols = [c['name'] for c in inspector.get_columns('evidence')]
    with op.batch_alter_table('evidence', schema=None) as batch_op:
        if 'evidence_text' not in ev_cols:
            batch_op.add_column(sa.Column('evidence_text', sa.Text(), nullable=False, server_default=''))
        if 'direction' not in ev_cols:
            batch_op.add_column(sa.Column('direction', sa.String(length=50), nullable=False, server_default='CONTEXTUAL'))
        if 'source_location' not in ev_cols:
            batch_op.add_column(sa.Column('source_location', sa.String(length=255), nullable=True))
        if 'relevance' not in ev_cols:
            batch_op.add_column(sa.Column('relevance', sa.String(length=20), nullable=False, server_default='MEDIUM'))
        if 'confidence_in_extraction' not in ev_cols:
            batch_op.add_column(sa.Column('confidence_in_extraction', sa.Float(), nullable=False, server_default='1.0'))
        if 'extraction_method' not in ev_cols:
            batch_op.add_column(sa.Column('extraction_method', sa.String(length=50), nullable=False, server_default='rule_based'))
        if 'extracted_at' not in ev_cols:
            batch_op.add_column(sa.Column('extracted_at', sa.DateTime(), nullable=True))

    # 2. Batch alter source_comparisons table
    sc_cols = [c['name'] for c in inspector.get_columns('source_comparisons')]
    with op.batch_alter_table('source_comparisons', schema=None) as batch_op:
        if 'source_a_id' not in sc_cols:
            batch_op.add_column(sa.Column('source_a_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_source_comparisons_source_a', 'sources', ['source_a_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index(op.f('ix_source_comparisons_source_a_id'), ['source_a_id'], unique=False)
        if 'source_b_id' not in sc_cols:
            batch_op.add_column(sa.Column('source_b_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_source_comparisons_source_b', 'sources', ['source_b_id'], ['id'], ondelete='SET NULL')
            batch_op.create_index(op.f('ix_source_comparisons_source_b_id'), ['source_b_id'], unique=False)
        if 'comparison_type' not in sc_cols:
            batch_op.add_column(sa.Column('comparison_type', sa.String(length=50), nullable=False, server_default='PAIRWISE'))
        if 'source_relationship' not in sc_cols:
            batch_op.add_column(sa.Column('source_relationship', sa.String(length=50), nullable=False, server_default='UNKNOWN'))
        if 'evidence_consistency' not in sc_cols:
            batch_op.add_column(sa.Column('evidence_consistency', sa.String(length=50), nullable=False, server_default='CONSISTENT_EVIDENCE'))
        if 'details' not in sc_cols:
            batch_op.add_column(sa.Column('details', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('source_comparisons', schema=None) as batch_op:
        batch_op.drop_column('details')
        batch_op.drop_column('evidence_consistency')
        batch_op.drop_column('source_relationship')
        batch_op.drop_column('comparison_type')
        batch_op.drop_index(op.f('ix_source_comparisons_source_b_id'))
        batch_op.drop_column('source_b_id')
        batch_op.drop_index(op.f('ix_source_comparisons_source_a_id'))
        batch_op.drop_column('source_a_id')

    with op.batch_alter_table('evidence', schema=None) as batch_op:
        batch_op.drop_column('extracted_at')
        batch_op.drop_column('extraction_method')
        batch_op.drop_column('confidence_in_extraction')
        batch_op.drop_column('relevance')
        batch_op.drop_column('source_location')
        batch_op.drop_column('direction')
        batch_op.drop_column('evidence_text')
