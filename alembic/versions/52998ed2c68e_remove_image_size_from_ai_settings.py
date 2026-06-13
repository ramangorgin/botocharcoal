"""remove_image_size_from_ai_settings

Revision ID: 52998ed2c68e
Revises: 26aab3aa1ba8
Create Date: 2026-06-13 23:50:46.167102
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '52998ed2c68e'
down_revision: Union[str, None] = '26aab3aa1ba8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('ai_settings', 'image_size')


def downgrade() -> None:
    op.add_column('ai_settings', sa.Column('image_size', sa.String(length=32), nullable=True))
