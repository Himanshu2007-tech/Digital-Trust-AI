"""add_part_4_source_and_search_query_fields

Revision ID: 3a3de1f1563e
Revises: 9cf667711b4f
Create Date: 2026-09-16 08:06:46.937042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a3de1f1563e'
down_revision: Union[str, None] = '9cf667711b4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    # 1. Create claim_sources table if not already created
    if 'claim_sources' not in tables:
        op.create_table('claim_sources',
            sa.Column('claim_id', sa.Integer(), nullable=False),
            sa.Column('source_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('claim_id', 'source_id')
        )

    # 2. Batch alter search_queries
    sq_cols = [c['name'] for c in inspector.get_columns('search_queries')]
    with op.batch_alter_table('search_queries', schema=None) as batch_op:
        if 'status' not in sq_cols:
            batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=False, server_default='success'))
        if 'error_message' not in sq_cols:
            batch_op.add_column(sa.Column('error_message', sa.Text(), nullable=True))

    # 3. Batch alter sources
    src_cols = [c['name'] for c in inspector.get_columns('sources')]
    with op.batch_alter_table('sources', schema=None) as batch_op:
        if 'canonical_url' not in src_cols:
            batch_op.add_column(sa.Column('canonical_url', sa.String(length=1024), nullable=True))
        if 'title' not in src_cols:
            batch_op.add_column(sa.Column('title', sa.String(length=512), nullable=True))
        if 'snippet' not in src_cols:
            batch_op.add_column(sa.Column('snippet', sa.Text(), nullable=True))
        if 'publisher' not in src_cols:
            batch_op.add_column(sa.Column('publisher', sa.String(length=255), nullable=True))
        if 'author' not in src_cols:
            batch_op.add_column(sa.Column('author', sa.String(length=255), nullable=True))
        if 'country' not in src_cols:
            batch_op.add_column(sa.Column('country', sa.String(length=100), nullable=True))
        if 'publication_date' not in src_cols:
            batch_op.add_column(sa.Column('publication_date', sa.String(length=100), nullable=True))
        if 'query_used' not in src_cols:
            batch_op.add_column(sa.Column('query_used', sa.String(length=512), nullable=True))
        if 'provider' not in src_cols:
            batch_op.add_column(sa.Column('provider', sa.String(length=50), nullable=True))
        if 'retrieved_at' not in src_cols:
            batch_op.add_column(sa.Column('retrieved_at', sa.DateTime(), nullable=True))
        if 'syndication_source' not in src_cols:
            batch_op.add_column(sa.Column('syndication_source', sa.String(length=255), nullable=True))

        batch_op.alter_column('url',
                   existing_type=sa.VARCHAR(length=512),
                   type_=sa.String(length=1024),
                   existing_nullable=True)
        batch_op.alter_column('credibility_score',
                   existing_type=sa.FLOAT(),
                   nullable=True)
        
        # Safe index update
        src_indexes = [idx['name'] for idx in inspector.get_indexes('sources')]
        if 'ix_sources_domain' in src_indexes:
            batch_op.drop_index('ix_sources_domain')
        batch_op.create_index(op.f('ix_sources_domain'), ['domain'], unique=False)
        if 'ix_sources_canonical_url' not in src_indexes:
            batch_op.create_index(op.f('ix_sources_canonical_url'), ['canonical_url'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('sources', schema=None) as batch_op:
        batch_op.drop_index(op.f('ix_sources_canonical_url'))
        batch_op.drop_index(op.f('ix_sources_domain'))
        batch_op.create_index('ix_sources_domain', ['domain'], unique=True)
        batch_op.alter_column('credibility_score',
                   existing_type=sa.FLOAT(),
                   nullable=False)
        batch_op.alter_column('url',
                   existing_type=sa.String(length=1024),
                   type_=sa.VARCHAR(length=512),
                   existing_nullable=True)
        batch_op.drop_column('syndication_source')
        batch_op.drop_column('retrieved_at')
        batch_op.drop_column('provider')
        batch_op.drop_column('query_used')
        batch_op.drop_column('publication_date')
        batch_op.drop_column('country')
        batch_op.drop_column('author')
        batch_op.drop_column('publisher')
        batch_op.drop_column('snippet')
        batch_op.drop_column('title')
        batch_op.drop_column('canonical_url')

    with op.batch_alter_table('search_queries', schema=None) as batch_op:
        batch_op.drop_column('error_message')
        batch_op.drop_column('status')

    op.drop_table('claim_sources')
