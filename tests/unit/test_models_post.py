"""
Tests for TNSE Post database models.

Following TDD methodology: these tests are written BEFORE the implementation.
Tests cover the Post, PostContent, and PostMedia models.

Requirements addressed:
- WS-1.2: Design schema for posts (content, timestamps)
- REQ-NP-002: System SHALL extract text, images, and video content
- REQ-NP-010: System SHOULD detect forwarded/reposted content
"""

import pytest
from datetime import datetime, timezone
from uuid import UUID, uuid4


class TestPostModel:
    """Tests for the Post database model."""

    def test_post_model_exists(self):
        """Test that Post model class exists and can be imported."""
        from src.tnse.db.models import Post
        assert Post is not None

    def test_post_has_required_fields(self):
        """Test that Post model has all required fields."""
        from src.tnse.db.models import Post

        column_names = [column.name for column in Post.__table__.columns]

        required_fields = [
            "id",
            "channel_id",
            "telegram_message_id",
            "published_at",
            "is_forwarded",
            "forward_from_channel_id",
            "forward_from_message_id",
            "created_at",
            "updated_at",
        ]

        for field in required_fields:
            assert field in column_names, f"Post model missing required field: {field}"

    def test_post_has_tablename(self):
        """Test that Post model has correct table name."""
        from src.tnse.db.models import Post

        assert Post.__tablename__ == "posts"

    def test_post_has_foreign_key_to_channel(self):
        """Test that Post has foreign key to Channel."""
        from src.tnse.db.models import Post

        channel_id_column = Post.__table__.columns["channel_id"]
        foreign_keys = list(channel_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "channels.id" in str(foreign_keys[0])

    def test_post_telegram_message_id_is_indexed(self):
        """Test that telegram_message_id is indexed for efficient lookups."""
        from src.tnse.db.models import Post

        telegram_msg_column = Post.__table__.columns["telegram_message_id"]
        assert telegram_msg_column.index is True or any(
            telegram_msg_column in idx.columns
            for idx in Post.__table__.indexes
        )

    def test_post_published_at_is_indexed(self):
        """Test that published_at is indexed for time-range queries."""
        from src.tnse.db.models import Post

        # Check either column has index or there's an index containing the column
        published_at_column = Post.__table__.columns["published_at"]
        has_index = published_at_column.index is True or any(
            published_at_column in idx.columns
            for idx in Post.__table__.indexes
        )
        assert has_index, "published_at should be indexed for time-range queries"

    def test_post_can_be_instantiated(self):
        """Test that Post can be instantiated with required fields."""
        from src.tnse.db.models import Post

        post = Post(
            channel_id=uuid4(),
            telegram_message_id=123456,
            published_at=datetime.now(timezone.utc),
        )

        assert post.telegram_message_id == 123456
        assert post.is_forwarded is False  # Default

    def test_post_is_forwarded_defaults_to_false(self):
        """Test that is_forwarded defaults to False."""
        from src.tnse.db.models import Post

        is_forwarded_column = Post.__table__.columns["is_forwarded"]
        assert is_forwarded_column.default is not None or is_forwarded_column.server_default is not None

    def test_post_has_unique_constraint_on_channel_and_message(self):
        """Test that there's a unique constraint on (channel_id, telegram_message_id)."""
        from src.tnse.db.models import Post

        # Check for unique constraint
        constraints = Post.__table__.constraints
        has_unique = False
        for constraint in constraints:
            if hasattr(constraint, 'columns'):
                col_names = [col.name for col in constraint.columns]
                if 'channel_id' in col_names and 'telegram_message_id' in col_names:
                    has_unique = True
                    break

        # Also check indexes for unique index
        for index in Post.__table__.indexes:
            col_names = [col.name for col in index.columns]
            if 'channel_id' in col_names and 'telegram_message_id' in col_names and index.unique:
                has_unique = True
                break

        assert has_unique, "Post should have unique constraint on (channel_id, telegram_message_id)"


class TestPostContentModel:
    """Tests for the PostContent database model."""

    def test_post_content_model_exists(self):
        """Test that PostContent model class exists."""
        from src.tnse.db.models import PostContent
        assert PostContent is not None

    def test_post_content_has_required_fields(self):
        """Test that PostContent has all required fields."""
        from src.tnse.db.models import PostContent

        column_names = [column.name for column in PostContent.__table__.columns]

        required_fields = [
            "id",
            "post_id",
            "text_content",
            "language",
            "created_at",
        ]

        for field in required_fields:
            assert field in column_names, f"PostContent missing required field: {field}"

    def test_post_content_has_tablename(self):
        """Test that PostContent has correct table name."""
        from src.tnse.db.models import PostContent

        assert PostContent.__tablename__ == "post_content"

    def test_post_content_has_foreign_key_to_post(self):
        """Test that PostContent has foreign key to Post."""
        from src.tnse.db.models import PostContent

        post_id_column = PostContent.__table__.columns["post_id"]
        foreign_keys = list(post_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "posts.id" in str(foreign_keys[0])

    def test_post_content_text_is_text_type(self):
        """Test that text_content can store large text."""
        from src.tnse.db.models import PostContent
        from sqlalchemy import Text

        text_column = PostContent.__table__.columns["text_content"]
        assert isinstance(text_column.type, Text)

    def test_post_content_has_one_to_one_with_post(self):
        """Test that PostContent has one-to-one relationship with Post."""
        from src.tnse.db.models import PostContent

        post_id_column = PostContent.__table__.columns["post_id"]
        assert post_id_column.unique is True


class TestPostMediaModel:
    """Tests for the PostMedia database model."""

    def test_post_media_model_exists(self):
        """Test that PostMedia model class exists."""
        from src.tnse.db.models import PostMedia
        assert PostMedia is not None

    def test_post_media_has_required_fields(self):
        """Test that PostMedia has all required fields."""
        from src.tnse.db.models import PostMedia

        column_names = [column.name for column in PostMedia.__table__.columns]

        required_fields = [
            "id",
            "post_id",
            "media_type",
            "file_id",
            "file_size",
            "mime_type",
            "duration",
            "width",
            "height",
            "thumbnail_file_id",
            "created_at",
        ]

        for field in required_fields:
            assert field in column_names, f"PostMedia missing required field: {field}"

    def test_post_media_has_tablename(self):
        """Test that PostMedia has correct table name."""
        from src.tnse.db.models import PostMedia

        assert PostMedia.__tablename__ == "post_media"

    def test_post_media_has_foreign_key_to_post(self):
        """Test that PostMedia has foreign key to Post."""
        from src.tnse.db.models import PostMedia

        post_id_column = PostMedia.__table__.columns["post_id"]
        foreign_keys = list(post_id_column.foreign_keys)

        assert len(foreign_keys) > 0
        assert "posts.id" in str(foreign_keys[0])

    def test_post_can_have_multiple_media(self):
        """Test that a post can have multiple media items (one-to-many)."""
        from src.tnse.db.models import PostMedia

        # post_id should NOT be unique (allows multiple media per post)
        post_id_column = PostMedia.__table__.columns["post_id"]
        assert post_id_column.unique is not True


class TestMediaTypeEnum:
    """Tests for media type enumeration."""

    def test_media_type_enum_exists(self):
        """Test that MediaType enum exists."""
        from src.tnse.db.models import MediaType
        assert MediaType is not None

    def test_media_type_has_photo_value(self):
        """Test that MediaType has PHOTO type."""
        from src.tnse.db.models import MediaType
        assert hasattr(MediaType, "PHOTO")

    def test_media_type_has_video_value(self):
        """Test that MediaType has VIDEO type."""
        from src.tnse.db.models import MediaType
        assert hasattr(MediaType, "VIDEO")

    def test_media_type_has_document_value(self):
        """Test that MediaType has DOCUMENT type."""
        from src.tnse.db.models import MediaType
        assert hasattr(MediaType, "DOCUMENT")

    def test_media_type_has_audio_value(self):
        """Test that MediaType has AUDIO type."""
        from src.tnse.db.models import MediaType
        assert hasattr(MediaType, "AUDIO")

    def test_media_type_has_animation_value(self):
        """Test that MediaType has ANIMATION type (for GIFs)."""
        from src.tnse.db.models import MediaType
        assert hasattr(MediaType, "ANIMATION")
