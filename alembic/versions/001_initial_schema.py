"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types for PostgreSQL
    op.execute("CREATE TYPE jobstatus AS ENUM ('pending', 'queued', 'processing', 'retrying', 'completed', 'failed')")
    op.execute("CREATE TYPE postwebsitestatus AS ENUM ('draft', 'published')")
    op.execute("CREATE TYPE postinstagramstatus AS ENUM ('not_published', 'published', 'failed')")
    op.execute("CREATE TYPE mediarole AS ENUM ('instagram', 'blog_cover')")

    # users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("username", name=op.f("uq_users_username")),
    )

    # jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=False),
        sa.Column("tone", sa.String(length=128), nullable=True),
        sa.Column("cta_text", sa.String(length=256), nullable=True),
        sa.Column("image_count", sa.Integer(), nullable=True, server_default="4"),
        sa.Column("status", sa.Enum("pending", "queued", "processing", "retrying", "completed", "failed", name="jobstatus"), nullable=True, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("logs_text", sa.Text(), nullable=True),
        sa.Column("generated_caption", sa.Text(), nullable=True),
        sa.Column("generated_hashtags", sa.Text(), nullable=True),
        sa.Column("generated_blog_title", sa.String(length=512), nullable=True),
        sa.Column("generated_blog_slug", sa.String(length=512), nullable=True),
        sa.Column("generated_blog_body", sa.Text(), nullable=True),
        sa.Column("generated_image_prompts", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(op.f("ix_jobs"), "jobs", ["id"], unique=False)

    # posts
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("slug", sa.String(length=512), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("instagram_caption", sa.Text(), nullable=True),
        sa.Column("hashtags", sa.Text(), nullable=True),
        sa.Column("website_status", sa.Enum("draft", "published", name="postwebsitestatus"), nullable=True, server_default="draft"),
        sa.Column("instagram_status", sa.Enum("not_published", "published", "failed", name="postinstagramstatus"), nullable=True, server_default="not_published"),
        sa.Column("instagram_media_id", sa.String(length=128), nullable=True),
        sa.Column("published_to_website_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_to_instagram_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_posts")),
        sa.UniqueConstraint("slug", name=op.f("uq_posts_slug")),
    )
    op.create_index(op.f("ix_posts"), "posts", ["id"], unique=False)

    # media_assets
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.Enum("instagram", "blog_cover", name="mediarole"), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("local_path", sa.String(length=1024), nullable=True),
        sa.Column("public_url", sa.String(length=1024), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], name=op.f("fk_media_assets_job_id_jobs"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], name=op.f("fk_media_assets_post_id_posts"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
    )
    op.create_index(op.f("ix_media_assets"), "media_assets", ["id"], unique=False)

    # leads
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("contacted", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_leads")),
    )
    op.create_index(op.f("ix_leads"), "leads", ["id"], unique=False)

    # catalogs
    op.create_table(
        "catalogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("public_url", sa.String(length=1024), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_catalogs")),
    )
    op.create_index(op.f("ix_catalogs"), "catalogs", ["id"], unique=False)

    # settings
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings")),
        sa.UniqueConstraint("key", name=op.f("uq_settings_key")),
    )
    op.create_index(op.f("ix_settings"), "settings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("settings")
    op.drop_table("catalogs")
    op.drop_table("leads")
    op.drop_table("media_assets")
    op.drop_table("posts")
    op.drop_table("jobs")
    op.drop_table("users")
    op.execute("DROP TYPE mediarole")
    op.execute("DROP TYPE postinstagramstatus")
    op.execute("DROP TYPE postwebsitestatus")
    op.execute("DROP TYPE jobstatus")
