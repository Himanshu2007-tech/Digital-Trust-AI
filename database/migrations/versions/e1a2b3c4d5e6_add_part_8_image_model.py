"""add_part_8_image_model

Revision ID: e1a2b3c4d5e6
Revises: d9f8e7a6b5c4
Create Date: 2026-09-28 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'd9f8e7a6b5c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if 'image_verifications' not in tables:
        op.create_table(
            'image_verifications',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('media_file_id', sa.Integer(), nullable=True),
            sa.Column('image_width', sa.Integer(), nullable=True),
            sa.Column('image_height', sa.Integer(), nullable=True),
            sa.Column('image_format', sa.String(length=50), nullable=True),
            sa.Column('raw_ocr_text', sa.Text(), nullable=False),
            sa.Column('normalized_ocr_text', sa.Text(), nullable=False),
            sa.Column('ocr_confidence', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('ocr_blocks', sa.JSON(), nullable=True),
            sa.Column('detected_urls', sa.JSON(), nullable=True),
            sa.Column('detected_entities', sa.JSON(), nullable=True),
            sa.Column('exif_metadata', sa.JSON(), nullable=True),
            sa.Column('ocr_engine', sa.String(length=50), nullable=False, server_default='tesseract'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['request_id'], ['verification_requests.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['media_file_id'], ['media_files.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_image_verifications_id'), 'image_verifications', ['id'], unique=False)
        op.create_index(op.f('ix_image_verifications_request_id'), 'image_verifications', ['request_id'], unique=False)
        op.create_index(op.f('ix_image_verifications_media_file_id'), 'image_verifications', ['media_file_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if 'image_verifications' in tables:
        op.drop_index(op.f('ix_image_verifications_media_file_id'), table_name='image_verifications')
        op.drop_index(op.f('ix_image_verifications_request_id'), table_name='image_verifications')
        op.drop_index(op.f('ix_image_verifications_id'), table_name='image_verifications')
        op.drop_table('image_verifications')
