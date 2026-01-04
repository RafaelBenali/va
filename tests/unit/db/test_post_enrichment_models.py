"""
Tests for Post Enrichment Database Models (WS-5.2)

Following TDD methodology: these tests are written BEFORE implementation.
The tests validate:
1. PostEnrichment model structure and fields
2. LLMUsageLog model structure and fields
3. Relationship from Post to PostEnrichment
4. Field validations and constraints
5. GIN index creation for keyword arrays
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestPostEnrichmentModel:
    """Tests for PostEnrichment SQLAlchemy model."""

    def test_post_enrichment_model_exists(self):
        """Test that PostEnrichment model can be imported."""
        from src.tnse.db.models import PostEnrichment

        assert PostEnrichment is not None

    def test_post_enrichment_has_required_fields(self):
        """Test that PostEnrichment has all required fields."""
        from src.tnse.db.models import PostEnrichment

        # Get the columns from the model
        mapper = inspect(PostEnrichment)
        column_names = [column.key for column in mapper.columns]

        # Required fields from WS-5.2 specification
        required_fields = [
            "id",
            "post_id",
            "explicit_keywords",
            "implicit_keywords",
            "category",
            "sentiment",
            "entities",
            "model_used",
            "token_count",
            "processing_time_ms",
            "enriched_at",
        ]

        for field in required_fields:
            assert field in column_names, f"Missing required field: {field}"

    def test_post_enrichment_table_name(self):
        """Test that PostEnrichment uses correct table name."""
        from src.tnse.db.models import PostEnrichment

        assert PostEnrichment.__tablename__ == "post_enrichments"

    def test_post_enrichment_post_id_is_foreign_key(self):
        """Test that post_id is a foreign key to posts table."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        post_id_column = mapper.columns["post_id"]

        # Check that it has a foreign key
        foreign_keys = list(post_id_column.foreign_keys)
        assert len(foreign_keys) == 1
        assert "posts.id" in str(foreign_keys[0])

    def test_post_enrichment_post_id_has_cascade_delete(self):
        """Test that post_id foreign key has CASCADE on delete."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        post_id_column = mapper.columns["post_id"]

        foreign_keys = list(post_id_column.foreign_keys)
        assert len(foreign_keys) == 1

        # Check for CASCADE delete
        fk = foreign_keys[0]
        assert fk.ondelete == "CASCADE"

    def test_post_enrichment_post_id_is_unique(self):
        """Test that post_id has a unique constraint (one enrichment per post)."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        post_id_column = mapper.columns["post_id"]

        assert post_id_column.unique is True

    def test_post_enrichment_explicit_keywords_is_array(self):
        """Test that explicit_keywords is a PostgreSQL ARRAY type."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["explicit_keywords"]

        # Check that the column type is ARRAY
        assert isinstance(column.type, ARRAY)

    def test_post_enrichment_implicit_keywords_is_array(self):
        """Test that implicit_keywords is a PostgreSQL ARRAY type."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["implicit_keywords"]

        # Check that the column type is ARRAY
        assert isinstance(column.type, ARRAY)

    def test_post_enrichment_entities_is_jsonb(self):
        """Test that entities is a PostgreSQL JSONB type."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["entities"]

        # Check that the column type is JSONB
        assert isinstance(column.type, JSONB)

    def test_post_enrichment_enriched_at_has_default(self):
        """Test that enriched_at has a default value."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["enriched_at"]

        # Check that it has a default
        assert column.default is not None or column.server_default is not None

    def test_post_enrichment_category_has_max_length(self):
        """Test that category field has appropriate max length."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["category"]

        # Check max length is 100 as per spec
        assert column.type.length == 100

    def test_post_enrichment_sentiment_has_max_length(self):
        """Test that sentiment field has appropriate max length."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        column = mapper.columns["sentiment"]

        # Check max length is 20 as per spec
        assert column.type.length == 20

    def test_post_enrichment_instance_creation(self):
        """Test that PostEnrichment instance can be created with valid data."""
        from src.tnse.db.models import PostEnrichment

        post_id = uuid.uuid4()
        enrichment = PostEnrichment(
            post_id=post_id,
            explicit_keywords=["corruption", "minister"],
            implicit_keywords=["politics", "scandal", "government"],
            category="politics",
            sentiment="negative",
            entities={
                "people": ["John Smith"],
                "organizations": ["Ministry of Finance"],
                "places": ["Kiev"],
            },
            model_used="groq/qwen-qwq-32b",
            token_count=150,
            processing_time_ms=500,
        )

        assert enrichment.post_id == post_id
        assert enrichment.explicit_keywords == ["corruption", "minister"]
        assert enrichment.implicit_keywords == ["politics", "scandal", "government"]
        assert enrichment.category == "politics"
        assert enrichment.sentiment == "negative"
        assert enrichment.entities["people"] == ["John Smith"]
        assert enrichment.model_used == "groq/qwen-qwq-32b"
        assert enrichment.token_count == 150
        assert enrichment.processing_time_ms == 500


class TestLLMUsageLogModel:
    """Tests for LLMUsageLog SQLAlchemy model."""

    def test_llm_usage_log_model_exists(self):
        """Test that LLMUsageLog model can be imported."""
        from src.tnse.db.models import LLMUsageLog

        assert LLMUsageLog is not None

    def test_llm_usage_log_has_required_fields(self):
        """Test that LLMUsageLog has all required fields."""
        from src.tnse.db.models import LLMUsageLog

        # Get the columns from the model
        mapper = inspect(LLMUsageLog)
        column_names = [column.key for column in mapper.columns]

        # Required fields from WS-5.2 specification
        required_fields = [
            "id",
            "model",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "task_name",
            "posts_processed",
            "created_at",
        ]

        for field in required_fields:
            assert field in column_names, f"Missing required field: {field}"

    def test_llm_usage_log_table_name(self):
        """Test that LLMUsageLog uses correct table name."""
        from src.tnse.db.models import LLMUsageLog

        assert LLMUsageLog.__tablename__ == "llm_usage_logs"

    def test_llm_usage_log_model_field_is_not_null(self):
        """Test that model field is required (not null)."""
        from src.tnse.db.models import LLMUsageLog

        mapper = inspect(LLMUsageLog)
        column = mapper.columns["model"]

        assert column.nullable is False

    def test_llm_usage_log_token_counts_are_not_null(self):
        """Test that token count fields are required."""
        from src.tnse.db.models import LLMUsageLog

        mapper = inspect(LLMUsageLog)

        for field_name in ["prompt_tokens", "completion_tokens", "total_tokens"]:
            column = mapper.columns[field_name]
            assert column.nullable is False, f"{field_name} should not be nullable"

    def test_llm_usage_log_estimated_cost_is_decimal(self):
        """Test that estimated_cost_usd uses appropriate decimal type."""
        from src.tnse.db.models import LLMUsageLog
        from sqlalchemy import Numeric

        mapper = inspect(LLMUsageLog)
        column = mapper.columns["estimated_cost_usd"]

        # Check that it's a Numeric type for precise decimal calculations
        assert isinstance(column.type, Numeric)

    def test_llm_usage_log_posts_processed_has_default(self):
        """Test that posts_processed has a default value of 1."""
        from src.tnse.db.models import LLMUsageLog

        mapper = inspect(LLMUsageLog)
        column = mapper.columns["posts_processed"]

        # Check that it has a default value
        assert column.default is not None

    def test_llm_usage_log_created_at_has_default(self):
        """Test that created_at has a default timestamp."""
        from src.tnse.db.models import LLMUsageLog

        mapper = inspect(LLMUsageLog)
        column = mapper.columns["created_at"]

        assert column.default is not None or column.server_default is not None

    def test_llm_usage_log_instance_creation(self):
        """Test that LLMUsageLog instance can be created with valid data."""
        from src.tnse.db.models import LLMUsageLog

        log = LLMUsageLog(
            model="groq/qwen-qwq-32b",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=Decimal("0.000058"),
            task_name="enrich_post",
            posts_processed=1,
        )

        assert log.model == "groq/qwen-qwq-32b"
        assert log.prompt_tokens == 100
        assert log.completion_tokens == 50
        assert log.total_tokens == 150
        assert log.estimated_cost_usd == Decimal("0.000058")
        assert log.task_name == "enrich_post"
        assert log.posts_processed == 1


class TestPostEnrichmentRelationship:
    """Tests for Post to PostEnrichment relationship."""

    def test_post_has_enrichment_relationship(self):
        """Test that Post model has an enrichment relationship."""
        from src.tnse.db.models import Post

        # Check that Post has enrichment attribute
        assert hasattr(Post, "enrichment")

    def test_post_enrichment_relationship_is_one_to_one(self):
        """Test that Post to PostEnrichment is a one-to-one relationship."""
        from src.tnse.db.models import Post

        mapper = inspect(Post)
        relationships = mapper.relationships

        # Find the enrichment relationship
        assert "enrichment" in relationships
        enrichment_rel = relationships["enrichment"]

        # Check it's uselist=False (one-to-one)
        assert enrichment_rel.uselist is False

    def test_post_enrichment_has_backref_to_post(self):
        """Test that PostEnrichment has a backref to Post."""
        from src.tnse.db.models import PostEnrichment

        mapper = inspect(PostEnrichment)
        relationships = mapper.relationships

        assert "post" in relationships


class TestPostEnrichmentModelRepr:
    """Tests for model string representation."""

    def test_post_enrichment_repr(self):
        """Test PostEnrichment __repr__ method."""
        from src.tnse.db.models import PostEnrichment

        post_id = uuid.uuid4()
        enrichment = PostEnrichment(
            id=uuid.uuid4(),
            post_id=post_id,
            category="politics",
        )

        repr_str = repr(enrichment)
        assert "PostEnrichment" in repr_str
        assert str(enrichment.id) in repr_str

    def test_llm_usage_log_repr(self):
        """Test LLMUsageLog __repr__ method."""
        from src.tnse.db.models import LLMUsageLog

        log = LLMUsageLog(
            id=uuid.uuid4(),
            model="groq/qwen-qwq-32b",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        repr_str = repr(log)
        assert "LLMUsageLog" in repr_str
        assert str(log.id) in repr_str
