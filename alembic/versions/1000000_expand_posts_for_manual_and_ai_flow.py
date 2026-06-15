"""expand posts for manual and ai flow

Revision ID: 8f4c1d2b7a10
Revises: 52998ed2c68e
Create Date: 2026-06-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "8f4c1d2b7a10"
down_revision = "52998ed2c68e"
branch_labels = None
depends_on = None


def upgrade() -> None:

    with op.batch_alter_table("posts", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "source_type",
                sa.String(length=20),
                nullable=False,
                server_default="manual",
            )
        )

        batch_op.add_column(
            sa.Column(
                "job_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "content_item_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "category",
                sa.String(length=255),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "summary",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "cover_image_url",
                sa.Text(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "blog_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "instagram_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "scheduled_for",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "ai_payload",
                sa.JSON(),
                nullable=True,
            )
        )

        batch_op.create_foreign_key(
            "fk_posts_job_id_jobs",
            "jobs",
            ["job_id"],
            ["id"],
            ondelete="SET NULL",
        )

        batch_op.create_foreign_key(
            "fk_posts_content_item_id_content_items",
            "content_items",
            ["content_item_id"],
            ["id"],
            ondelete="SET NULL",
        )

        batch_op.create_index(
            "ix_posts_source_type",
            ["source_type"],
            unique=False,
        )

        batch_op.create_index(
            "ix_posts_job_id",
            ["job_id"],
            unique=False,
        )

        batch_op.create_index(
            "ix_posts_content_item_id",
            ["content_item_id"],
            unique=False,
        )

        batch_op.create_index(
            "ix_posts_scheduled_for",
            ["scheduled_for"],
            unique=False,
        )

    # حذف default بعد از migrate شدن
    with op.batch_alter_table("posts", schema=None) as batch_op:

        batch_op.alter_column(
            "source_type",
            server_default=None,
        )

        batch_op.alter_column(
            "blog_enabled",
            server_default=None,
        )

        batch_op.alter_column(
            "instagram_enabled",
            server_default=None,
        )


def downgrade() -> None:

    with op.batch_alter_table("posts", schema=None) as batch_op:

        batch_op.drop_index("ix_posts_scheduled_for")
        batch_op.drop_index("ix_posts_content_item_id")
        batch_op.drop_index("ix_posts_job_id")
        batch_op.drop_index("ix_posts_source_type")

        batch_op.drop_constraint(
            "fk_posts_content_item_id_content_items",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "fk_posts_job_id_jobs",
            type_="foreignkey",
        )

        batch_op.drop_column("ai_payload")
        batch_op.drop_column("scheduled_for")
        batch_op.drop_column("instagram_enabled")
        batch_op.drop_column("blog_enabled")
        batch_op.drop_column("cover_image_url")
        batch_op.drop_column("summary")
        batch_op.drop_column("category")
        batch_op.drop_column("content_item_id")
        batch_op.drop_column("job_id")
        batch_op.drop_column("source_type")
