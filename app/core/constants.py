from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class PostWebsiteStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"


class PostInstagramStatus(str, Enum):
    NOT_PUBLISHED = "not_published"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaRole(str, Enum):
    INSTAGRAM = "instagram"
    BLOG_COVER = "blog_cover"


INSTAGRAM_IMAGE_SIZE = (1080, 1350)
BLOG_COVER_SIZE = (1200, 630)
