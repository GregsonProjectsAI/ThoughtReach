"""Add content_fingerprint to conversation

Revision ID: f3a2c1d89e45
Revises: e19136684e87
Create Date: 2026-03-24 12:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'f3a2c1d89e45'
down_revision: Union[str, None] = 'e19136684e87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('conversations', sa.Column('content_fingerprint', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq_conversations_content_fingerprint', 'conversations', ['content_fingerprint'])


def downgrade() -> None:
    op.drop_constraint('uq_conversations_content_fingerprint', 'conversations', type_='unique')
    op.drop_column('conversations', 'content_fingerprint')
