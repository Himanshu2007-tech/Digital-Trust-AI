"""add_part_7_article_model

Revision ID: d9f8e7a6b5c4
Revises: c82f9952b143
Create Date: 2026-09-27 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9f8e7a6b5c4'
down_revision: Union[str, None] = 'c82f9952b143'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create articles table if not already created
    if 'articles' not in tables:
        op.create_table(
            'articles',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.Integer(), nullable=False),
            sa.Column('original_url', sa.String(length=2048), nullable=False),
            sa.Column('canonical_url', sa.String(length=2048), nullable=True),
            sa.Column('domain', sa.String(length=255), nullable=False),
            sa.Column('title', sa.String(length=512), nullable=True),
            sa.Column('publisher', sa.String(length=255), nullable=True),
            sa.Column('author', sa.String(length=255), nullable=True),
            sa.Column('published_at', sa.String(length=100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('language', sa.String(length=20), nullable=True),
            sa.Column('featured_image_url', sa.String(length=2048), nullable=True),
            sa.Column('article_text', sa.Text(), nullable=False),
            sa.Column('content_hash', sa.String(length=64), nullable=False),
            sa.Column('content_length', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('extraction_method', sa.String(length=50), nullable=False, server_default='readability_bs4'),
            sa.Column('retrieval_status', sa.String(length=50), nullable=False, server_default='success'),
            sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(['request_id'], ['verification_requests.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_articles_id'), 'articles', ['id'], unique=False)
        op.create_index(op.f('ix_articles_request_id'), 'articles', ['request_id'], unique=False)
        op.create_index(op.f('ix_articles_canonical_url'), 'articles', ['canonical_url'], unique=False)
        op.create_index(op.f('ix_articles_domain'), 'articles', ['domain'], unique=False)
        op.create_index(op.f('ix_articles_content_hash'), 'articles', ['content_hash'], unique=False)

    # 2. Add source_role to sources table if not present
    src_cols = [c['name'] for c in inspector.get_columns('sources')]
    with op.batch_alter_table('sources', schema=None) as batch_op:
        if 'source_role' not in src_cols:
            batch_op.add_column(
                sa.Column('source_role', sa.String(length=50), nullable=False, server_default='INDEPENDENT_SOURCE')
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    src_cols = [c['name'] for c in inspector.get_columns('sources')]

    with op.batch_alter_table('sources', schema=None) as batch_op:
        if 'source_role' in src_cols:
            batch_op.drop_column('source_role')

    tables = inspector.get_table_names()
    if 'articles' in tables:
        op.drop_index(op.f('ix_articles_content_hash'), table_name='articles')
        op.drop_index(op.f('ix_articles_domain'), table_name='articles')
        op.drop_index(op.f('ix_articles_canonical_url'), table_name='articles')
        op.drop_index(op.f('ix_articles_request_id'), table_name='articles')
        op.drop_index(op.f('ix_articles_id'), table_name='articles')
        op.drop_table('articles')
