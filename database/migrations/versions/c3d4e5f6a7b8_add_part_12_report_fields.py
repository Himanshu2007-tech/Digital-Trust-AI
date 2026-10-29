"""add_part_12_report_fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'reports' in tables:
        rep_cols = [c['name'] for c in inspector.get_columns('reports')]
        with op.batch_alter_table('reports', schema=None) as batch_op:
            if 'report_uuid' not in rep_cols:
                batch_op.add_column(sa.Column('report_uuid', sa.String(length=64), nullable=True))
            if 'file_size_bytes' not in rep_cols:
                batch_op.add_column(sa.Column('file_size_bytes', sa.Integer(), nullable=True))
            if 'mime_type' not in rep_cols:
                batch_op.add_column(sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='application/pdf'))
            if 'sha256_hash' not in rep_cols:
                batch_op.add_column(sa.Column('sha256_hash', sa.String(length=64), nullable=True))
            if 'version' not in rep_cols:
                batch_op.add_column(sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0'))
            if 'generated_at' not in rep_cols:
                batch_op.add_column(sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True))
            if 'error_message' not in rep_cols:
                batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))
            if 'generation_time_ms' not in rep_cols:
                batch_op.add_column(sa.Column('generation_time_ms', sa.Integer(), nullable=True))

            rep_indexes = [idx['name'] for idx in inspector.get_indexes('reports')]
            if 'ix_reports_report_uuid' not in rep_indexes:
                batch_op.create_index('ix_reports_report_uuid', ['report_uuid'], unique=True)
            if 'ix_reports_created_at' not in rep_indexes:
                batch_op.create_index('ix_reports_created_at', ['created_at'], unique=False)
            if 'ix_reports_status' not in rep_indexes:
                batch_op.create_index('ix_reports_status', ['status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('reports', schema=None) as batch_op:
        batch_op.drop_index('ix_reports_status')
        batch_op.drop_index('ix_reports_created_at')
        batch_op.drop_index('ix_reports_report_uuid')
        batch_op.drop_column('generation_time_ms')
        batch_op.drop_column('error_message')
        batch_op.drop_column('generated_at')
        batch_op.drop_column('version')
        batch_op.drop_column('sha256_hash')
        batch_op.drop_column('mime_type')
        batch_op.drop_column('file_size_bytes')
        batch_op.drop_column('report_uuid')
