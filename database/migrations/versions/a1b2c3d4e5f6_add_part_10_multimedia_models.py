"""add_part_10_multimedia_models

Revision ID: a1b2c3d4e5f6
Revises: f2b3c4d5e6f7
Create Date: 2026-09-29 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create video_frames table
    if 'video_frames' not in tables:
        op.create_table(
            'video_frames',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('media_verification_id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.Float(), nullable=False),
            sa.Column('frame_number', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('width', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('height', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('selection_method', sa.String(length=50), nullable=False, server_default='FIXED_INTERVAL'),
            sa.Column('image_hash', sa.String(length=64), nullable=False),
            sa.Column('stored_path', sa.String(length=500), nullable=True),
            sa.Column('ocr_text', sa.Text(), nullable=True),
            sa.Column('ocr_confidence', sa.Float(), nullable=True),
            sa.Column('ocr_blocks', sa.JSON(), nullable=True),
            sa.Column('visual_context', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['media_verification_id'], ['media_verifications.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_video_frames_id'), 'video_frames', ['id'], unique=False)
        op.create_index(op.f('ix_video_frames_media_verification_id'), 'video_frames', ['media_verification_id'], unique=False)
        op.create_index(op.f('ix_video_frames_timestamp'), 'video_frames', ['timestamp'], unique=False)
        op.create_index(op.f('ix_video_frames_image_hash'), 'video_frames', ['image_hash'], unique=False)

    # 2. Create claim_occurrences table
    if 'claim_occurrences' not in tables:
        op.create_table(
            'claim_occurrences',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('claim_id', sa.Integer(), nullable=False),
            sa.Column('media_verification_id', sa.Integer(), nullable=False),
            sa.Column('source_type', sa.String(length=50), nullable=False),
            sa.Column('timestamp_start', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('timestamp_end', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('frame_id', sa.Integer(), nullable=True),
            sa.Column('transcript_segment_id', sa.Integer(), nullable=True),
            sa.Column('ocr_block_id', sa.Integer(), nullable=True),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['media_verification_id'], ['media_verifications.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['frame_id'], ['video_frames.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['transcript_segment_id'], ['transcript_segments.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_claim_occurrences_id'), 'claim_occurrences', ['id'], unique=False)
        op.create_index(op.f('ix_claim_occurrences_claim_id'), 'claim_occurrences', ['claim_id'], unique=False)
        op.create_index(op.f('ix_claim_occurrences_media_verification_id'), 'claim_occurrences', ['media_verification_id'], unique=False)
        op.create_index(op.f('ix_claim_occurrences_source_type'), 'claim_occurrences', ['source_type'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'claim_occurrences' in tables:
        op.drop_table('claim_occurrences')
    if 'video_frames' in tables:
        op.drop_table('video_frames')
