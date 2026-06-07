"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():

    bind = op.get_bind()

    # ---------- ENUM DEFINITIONS ----------
    jobstatus_enum = postgresql.ENUM(
        "pending",
        "queued",
        "processing",
        "retrying",
        "completed",
        "failed",
        name="jobstatus",
        create_type=False,
    )

    postwebsitestatus_enum = postgresql.ENUM(
        "draft",
        "published",
        name="postwebsitestatus",
        create_type=False,
    )

    postinstagramstatus_enum = postgresql.ENUM(
        "not_published",
        "published",
        "failed",
        name="postinstagramstatus",
        create_type=False,
    )

    mediarole_enum = postgresql.ENUM(
        "instagram",
        "blog_cover",
        name="mediarole",
        create_type=False,
    )

    # ---------- CREATE ENUMS SAFELY ----------
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'jobstatus') THEN
            CREATE TYPE jobstatus AS ENUM ('pending','queued','processing','retrying','completed','failed');
        END IF;
    END$$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'postwebsitestatus') THEN
            CREATE TYPE postwebsitestatus AS ENUM ('draft','published');
        END IF;
    END$$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'postinstagramstatus') THEN
            CREATE TYPE postinstagramstatus AS ENUM ('not_published','published','failed');
        END IF;
    END$$;
    """)

    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mediarole') THEN
            CREATE TYPE mediarole AS ENUM ('instagram','blog_cover');
        END IF;
    END$$;
    """)

    # ---------- USERS ----------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # ---------- JOBS ----------
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("topic", sa.String(512), nullable=False),
        sa.Column("tone", sa.String(128)),
        sa.Column("cta_text", sa.String(256)),
        sa.Column("image_count", sa.Integer, server_default="4"),
        sa.Column("status", jobstatus_enum, server_default="pending"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("error_message", sa.Text),
        sa.Column("logs_text", sa.Text),
        sa.Column("generated_caption", sa.Text),
        sa.Column("generated_hashtags", sa.Text),
        sa.Column("generated_blog_title", sa.String(512)),
        sa.Column("generated_blog_slug", sa.String(512)),
        sa.Column("generated_blog_body", sa.Text),
        sa.Column("generated_image_prompts", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ---------- POSTS ----------
    op.create_table(
        "posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("topic", sa.String(512)),
        sa.Column("title", sa.String(512)),
        sa.Column("slug", sa.String(512), nullable=False, unique=True),
        sa.Column("body_html", sa.Text),
        sa.Column("instagram_caption", sa.Text),
        sa.Column("hashtags", sa.Text),
        sa.Column("website_status", postwebsitestatus_enum, server_default="draft"),
        sa.Column("instagram_status", postinstagramstatus_enum, server_default="not_published"),
        sa.Column("instagram_media_id", sa.String(128)),
        sa.Column("published_to_website_at", sa.DateTime(timezone=True)),
        sa.Column("published_to_instagram_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )

    # ---------- MEDIA ----------
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("post_id", sa.Integer),
        sa.Column("job_id", sa.Integer),
        sa.Column("role", mediarole_enum),
        sa.Column("prompt", sa.Text),
        sa.Column("local_path", sa.String(1024)),
        sa.Column("public_url", sa.String(1024)),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("sort_order", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
    )

    # ---------- LEADS ----------
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(128)),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("city", sa.String(128)),
        sa.Column("message", sa.Text),
        sa.Column("contacted", sa.Boolean, server_default="false"),
        sa.Column("contacted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # ---------- CATALOGS ----------
    op.create_table(
        "catalogs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("title", sa.String(256)),
        sa.Column("file_path", sa.String(1024)),
        sa.Column("public_url", sa.String(1024)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True)),
    )

    # ---------- SETTINGS ----------
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(128), nullable=False, unique=True),
        sa.Column("value", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )


def downgrade():

    op.drop_table("settings")
    op.drop_table("catalogs")
    op.drop_table("leads")
    op.drop_table("media_assets")
    op.drop_table("posts")
    op.drop_table("jobs")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS mediarole")
    op.execute("DROP TYPE IF EXISTS postinstagramstatus")
    op.execute("DROP TYPE IF EXISTS postwebsitestatus")
    op.execute("DROP TYPE IF EXISTS jobstatus")
