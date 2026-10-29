"""add_part_11_history_and_events

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-12 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create verification_events table if not exists
    if 'verification_events' not in tables:
        op.create_table(
            'verification_events',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('stage_name', sa.String(length=100), nullable=False),
            sa.Column('event_type', sa.String(length=100), nullable=False),
            sa.Column('status', sa.String(length=50), nullable=False, server_default='success'),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['request_id'], ['verification_requests.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_verification_events_id', 'verification_events', ['id'], unique=False)
        op.create_index('ix_verification_events_request_id', 'verification_events', ['request_id'], unique=False)
        op.create_index('ix_verification_events_event_type', 'verification_events', ['event_type'], unique=False)
        op.create_index('ix_verification_events_created_at', 'verification_events', ['created_at'], unique=False)

    # 2. Add columns and indexes to verification_requests
    vr_cols = [c['name'] for c in inspector.get_columns('verification_requests')]
    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        if 'content_hash' not in vr_cols:
            batch_op.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
            batch_op.create_index('ix_verification_requests_content_hash', ['content_hash'], unique=False)

        if 'completed_at' not in vr_cols:
            batch_op.add_column(sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
            batch_op.create_index('ix_verification_requests_completed_at', ['completed_at'], unique=False)

        if 'is_archived' not in vr_cols:
            batch_op.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('0')))
            batch_op.create_index('ix_verification_requests_is_archived', ['is_archived'], unique=False)

        if 'parent_request_id' not in vr_cols:
            batch_op.add_column(sa.Column('parent_request_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_verification_requests_parent_id',
                'verification_requests',
                ['parent_request_id'],
                ['id'],
                ondelete='SET NULL'
            )
            batch_op.create_index('ix_verification_requests_parent_request_id', ['parent_request_id'], unique=False)

        if 'error_message' not in vr_cols:
            batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))

        # Additional performance indexes
        vr_indexes = [idx['name'] for idx in inspector.get_indexes('verification_requests')]
        if 'ix_verification_requests_created_at' not in vr_indexes:
            batch_op.create_index('ix_verification_requests_created_at', ['created_at'], unique=False)
        if 'ix_verification_requests_type_status' not in vr_indexes:
            batch_op.create_index('ix_verification_requests_type_status', ['request_type', 'status'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('verification_requests', schema=None) as batch_op:
        batch_op.drop_index('ix_verification_requests_type_status')
        batch_op.drop_index('ix_verification_requests_created_at')
        batch_op.drop_index('ix_verification_requests_parent_request_id')
        batch_op.drop_constraint('fk_verification_requests_parent_id', type_='foreignkey')
        batch_op.drop_column('error_message')
        batch_op.drop_column('parent_request_id')
        batch_op.drop_index('ix_verification_requests_is_archived')
        batch_op.drop_column('is_archived')
        batch_op.drop_index('ix_verification_requests_completed_at')
        batch_op.drop_column('completed_at')
        batch_op.drop_index('ix_verification_requests_content_hash')
        batch_op.drop_column('content_hash')

    op.drop_index('ix_verification_events_created_at', table_name='verification_events')
    op.drop_index('ix_verification_events_event_type', table_name='verification_events')
    op.drop_index('ix_verification_events_request_id', table_name='verification_events')
    op.drop_index('ix_verification_events_id', table_name='verification_events')
    op.drop_table('verification_events')
