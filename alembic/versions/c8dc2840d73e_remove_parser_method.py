"""Remove parser_method

Revision ID: c8dc2840d73e
Revises: 29f770e2a655
Create Date: 2026-04-13 11:06:51.564422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8dc2840d73e'
down_revision: Union[str, None] = '29f770e2a655'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_column('conversations', 'parser_method')

def downgrade() -> None:
    op.add_column('conversations', sa.Column('parser_method', sa.String(), nullable=True))
