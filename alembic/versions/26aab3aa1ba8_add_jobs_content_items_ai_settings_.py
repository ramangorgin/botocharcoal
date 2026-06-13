"""add_jobs_content_items_ai_settings_tables

Revision ID: 26aab3aa1ba8
Revises: 6a9bbf0eaf65
Create Date: 2026-06-13 18:33:20.294761

Migration notes:
- The original jobs table had columns: topic, tone, cta_text, image_count,
  generated_caption, generated_hashtags, generated_blog_title, etc.
- The new Job model uses: subject, instructions, duration_days, start_date,
  items_per_day, auto_publish_blog, blog_image_count, instagram_image_count, etc.
- This migration ADDS new columns to the jobs table (keeps old ones for safety).
- Creates the content_items and ai_settings tables.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '26aab3aa1ba8'
down_revision: Union[str, None] = '6a9bbf0eaf65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ========== ADD NEW COLUMNS TO JOBS TABLE ==========
    # Note: retry_count and error_message already exist from the initial migration
    op.add_column('jobs', sa.Column('subject', sa.String(512), nullable=True))
    op.add_column('jobs', sa.Column('instructions', sa.Text, nullable=True))
    op.add_column('jobs', sa.Column('duration_days', sa.Integer, server_default='1'))
    op.add_column('jobs', sa.Column('start_date', sa.Date, nullable=True))
    op.add_column('jobs', sa.Column('items_per_day', sa.Integer, server_default='1'))
    op.add_column('jobs', sa.Column('auto_publish_blog', sa.Boolean, server_default='false'))
    op.add_column('jobs', sa.Column('blog_image_count', sa.Integer, server_default='1'))
    op.add_column('jobs', sa.Column('instagram_image_count', sa.Integer, server_default='4'))
    op.add_column('jobs', sa.Column('job_type', sa.String(64), server_default='general'))
    op.add_column('jobs', sa.Column('blog_title', sa.String(512), nullable=True))
    op.add_column('jobs', sa.Column('blog_slug', sa.String(512), nullable=True))
    op.add_column('jobs', sa.Column('blog_body', sa.Text, nullable=True))

    # Data migration: map old columns to new
    op.execute("""
        UPDATE jobs SET subject = topic WHERE subject IS NULL AND topic IS NOT NULL;
    """)
    op.execute("""
        UPDATE jobs SET 
            blog_title = generated_blog_title,
            blog_slug = generated_blog_slug,
            blog_body = generated_blog_body
        WHERE blog_title IS NULL AND generated_blog_title IS NOT NULL;
    """)

    # ========== CREATE CONTENT ITEMS TABLE ==========
    op.create_table(
        'content_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('jobs.id', ondelete='CASCADE')),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM(
            'pending', 'queued', 'processing', 'retrying', 'completed', 'failed',
            name='contentitemstatus',
            create_type=True,
        ), server_default='pending'),
        sa.Column('instagram_caption', sa.Text(), nullable=True),
        sa.Column('instagram_hashtags', sa.Text(), nullable=True),
        sa.Column('instagram_image_urls', sa.Text(), nullable=True),
        sa.Column('blog_title', sa.String(512), nullable=True),
        sa.Column('blog_slug', sa.String(512), nullable=True),
        sa.Column('blog_body', sa.Text(), nullable=True),
        sa.Column('blog_image_urls', sa.Text(), nullable=True),
        sa.Column('ai_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # ========== CREATE AI SETTINGS TABLE ==========
    op.create_table(
        'ai_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('provider', sa.String(32), server_default='openai'),
        sa.Column('api_key', sa.String(512), nullable=True),
        sa.Column('api_base_url', sa.String(512), nullable=True),
        sa.Column('text_model', sa.String(128), nullable=True),
        sa.Column('image_model', sa.String(128), nullable=True),
        sa.Column('image_size', sa.String(32), nullable=True),
        sa.Column('prompt_template', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('ai_settings')
    op.drop_table('content_items')
    op.drop_column('jobs', 'subject')
    op.drop_column('jobs', 'instructions')
    op.drop_column('jobs', 'duration_days')
    op.drop_column('jobs', 'start_date')
    op.drop_column('jobs', 'items_per_day')
    op.drop_column('jobs', 'auto_publish_blog')
    op.drop_column('jobs', 'blog_image_count')
    op.drop_column('jobs', 'instagram_image_count')
    op.drop_column('jobs', 'job_type')
    op.drop_column('jobs', 'retry_count')
    op.drop_column('jobs', 'error_message')
    op.drop_column('jobs', 'blog_title')
    op.drop_column('jobs', 'blog_slug')
    op.drop_column('jobs', 'blog_body')
    op.drop_type('contentitemstatus')
