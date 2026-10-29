"""add_part_9_media_model

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5e6
Create Date: 2026-09-29 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2b3c4d5e6f7'
down_revision: Union[str, None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create media_verifications table
    if 'media_verifications' not in tables:
        op.create_table(
            'media_verifications',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('media_file_id', sa.Integer(), nullable=True),
            sa.Column('media_type', sa.String(length=20), nullable=False),
            sa.Column('duration_seconds', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('width', sa.Integer(), nullable=True),
            sa.Column('height', sa.Integer(), nullable=True),
            sa.Column('media_hash', sa.String(length=64), nullable=False),
            sa.Column('audio_codec', sa.String(length=50), nullable=True),
            sa.Column('video_codec', sa.String(length=50), nullable=True),
            sa.Column('sample_rate', sa.Integer(), nullable=True),
            sa.Column('channels', sa.Integer(), nullable=True),
            sa.Column('bitrate', sa.Integer(), nullable=True),
            sa.Column('has_audio_track', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('language', sa.String(length=20), nullable=True, server_default='en'),
            sa.Column('raw_transcript', sa.Text(), nullable=False),
            sa.Column('normalized_transcript', sa.Text(), nullable=False),
            sa.Column('transcription_confidence', sa.Float(), nullable=True),
            sa.Column('detected_urls', sa.JSON(), nullable=True),
            sa.Column('detected_quotes', sa.JSON(), nullable=True),
            sa.Column('technical_indicators', sa.JSON(), nullable=True),
            sa.Column('metadata_json', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['request_id'], ['verification_requests.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['media_file_id'], ['media_files.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_media_verifications_id'), 'media_verifications', ['id'], unique=False)
        op.create_index(op.f('ix_media_verifications_request_id'), 'media_verifications', ['request_id'], unique=False)
        op.create_index(op.f('ix_media_verifications_media_file_id'), 'media_verifications', ['media_file_id'], unique=False)
        op.create_index(op.f('ix_media_verifications_media_type'), 'media_verifications', ['media_type'], unique=False)
        op.create_index(op.f('ix_media_verifications_media_hash'), 'media_verifications', ['media_hash'], unique=False)

    # 2. Create transcript_segments table
    if 'transcript_segments' not in tables:
        op.create_table(
            'transcript_segments',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('media_verification_id', sa.Integer(), nullable=False),
            sa.Column('sequence', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('start_time', sa.Float(), nullable=False),
            sa.Column('end_time', sa.Float(), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['media_verification_id'], ['media_verifications.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_transcript_segments_id'), 'transcript_segments', ['id'], unique=False)
        op.create_index(op.f('ix_transcript_segments_media_verification_id'), 'transcript_segments', ['media_verification_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'transcript_segments' in tables:
        op.drop_index(op.f('ix_transcript_segments_media_verification_id'), table_name='transcript_segments')
        op.drop_index(op.f('ix_transcript_segments_id'), table_name='transcript_segments')
        op.drop_table('transcript_segments')

    if 'media_verifications' in tables:
        op.drop_index(op.f('ix_media_verifications_media_hash'), table_name='media_verifications')
        op.drop_index(op.f('ix_media_verifications_media_type'), table_name='media_verifications')
        op.drop_index(op.f('ix_media_verifications_media_file_id'), table_name='media_verifications')
        op.drop_index(op.f('ix_media_verifications_request_id'), table_name='media_verifications')
        op.drop_index(op.f('ix_media_verifications_id'), table_name='media_verifications')
        op.drop_table('media_verifications')
