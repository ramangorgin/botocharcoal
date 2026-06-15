"""add poster column to posts

Revision ID: 00002_poster
Revises: 8f4c1d2b7a10
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = '00002_add_poster'
down_revision = '8f4c1d2b7a10'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('posts', sa.Column('poster', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('posts', 'poster')
