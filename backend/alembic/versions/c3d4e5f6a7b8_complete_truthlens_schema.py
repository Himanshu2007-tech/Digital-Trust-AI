"""complete_truthlens_schema

Revision ID: c3d4e5f6a7b8
Revises: 
Create Date: 2026-10-14 19:21:44.308237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.models import Base
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app.models import Base
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

