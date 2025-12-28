"""
TNSE API and Database Optimization Tests

Work Stream: WS-6.4 - API Design and Database Optimization

These tests verify:
1. FastAPI router organization best practices
2. Pydantic v2 model patterns
3. Database index optimization
4. N+1 query prevention
5. Redis usage patterns
6. Celery task error handling
7. Connection pooling configuration

Requirements addressed:
- API response times within targets
- Database queries optimized
- Connection pools properly configured
- Celery tasks properly retrying on failure
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


class TestFastAPIRouterOrganization:
    """Tests for FastAPI router organization and best practices."""

    def test_app_has_proper_metadata(self) -> None:
        """Test that FastAPI app has proper metadata for OpenAPI docs."""
        from src.tnse.main import app

        assert app.title is not None
        assert app.description is not None
        assert app.version is not None
        assert len(app.title) > 0
        assert len(app.description) > 0

    def test_health_endpoints_have_proper_response_models(self) -> None:
        """Test that health endpoints return structured responses."""
        from src.tnse.main import app

        client = TestClient(app)

        # Check /health endpoint
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

        # Check /liveness endpoint
        response = client.get("/liveness")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data

    def test_api_endpoints_use_proper_http_methods(self) -> None:
        """Test that API endpoints use correct HTTP methods."""
        from src.tnse.main import app

        # Health check endpoints should be GET
        routes = {route.path: route.methods for route in app.routes if hasattr(route, "methods")}

        assert "GET" in routes.get("/health", set())
        assert "GET" in routes.get("/liveness", set())
        assert "GET" in routes.get("/readiness", set())

    def test_app_uses_lifespan_context_manager(self) -> None:
        """Test that app uses modern lifespan context manager pattern."""
        from src.tnse.main import app

        # Modern FastAPI apps should use lifespan instead of on_event
        assert app.router.lifespan_context is not None


class TestPydanticV2Patterns:
    """Tests for Pydantic v2 model patterns and best practices."""

    def test_settings_uses_pydantic_settings_v2(self) -> None:
        """Test that settings uses pydantic-settings v2 patterns."""
        from src.tnse.core.config import Settings

        # Pydantic v2 uses model_config instead of Config class
        assert hasattr(Settings, "model_config")

    def test_settings_has_proper_validation(self) -> None:
        """Test that settings have proper field validation."""
        from src.tnse.core.config import Settings, get_settings

        # Test that validation works
        settings = get_settings()

        # Log level should be validated
        assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def test_nested_settings_use_pydantic_v2(self) -> None:
        """Test that nested settings use Pydantic v2 patterns."""
        from src.tnse.core.config import DatabaseSettings, RedisSettings

        # Check DatabaseSettings uses v2 patterns
        assert hasattr(DatabaseSettings, "model_config")

        # Check RedisSettings uses v2 patterns
        assert hasattr(RedisSettings, "model_config")

    def test_settings_uses_field_validator(self) -> None:
        """Test that settings use Pydantic v2 field_validator decorator."""
        from src.tnse.core.config import Settings
        import inspect

        # Check that validators are using v2 pattern
        source = inspect.getsource(Settings)
        assert "field_validator" in source or "@validator" not in source

    def test_search_result_is_properly_typed(self) -> None:
        """Test that SearchResult dataclass has proper type annotations."""
        from src.tnse.search.service import SearchResult
        import typing

        # Verify type hints are present
        hints = typing.get_type_hints(SearchResult)

        assert "post_id" in hints
        assert "channel_id" in hints
        assert "view_count" in hints
        assert "published_at" in hints


class TestDatabaseIndexOptimization:
    """Tests for database index optimization."""

    def test_posts_table_has_published_at_index(self) -> None:
        """Test that posts table has index on published_at for time-based queries."""
        from src.tnse.db.models import Post

        # Check table args for index
        table_args = Post.__table_args__
        index_names = [
            idx.name for idx in table_args
            if hasattr(idx, "name") and idx.name is not None
        ]

        assert "ix_posts_published_at" in index_names

    def test_engagement_metrics_has_post_id_index(self) -> None:
        """Test that engagement_metrics has index on post_id for JOIN queries."""
        from src.tnse.db.models import EngagementMetrics

        # The post_id column should have index=True
        column = EngagementMetrics.__table__.columns["post_id"]
        assert column.index is True or any(
            idx.columns.contains_column(column)
            for idx in EngagementMetrics.__table__.indexes
        )

    def test_engagement_metrics_has_collected_at_index(self) -> None:
        """Test that engagement_metrics has index on collected_at for sorting."""
        from src.tnse.db.models import EngagementMetrics

        # Check table args for index
        table_args = EngagementMetrics.__table_args__
        index_found = any(
            hasattr(idx, "name") and "collected_at" in (idx.name or "")
            for idx in table_args
        )
        assert index_found

    def test_channels_has_username_index(self) -> None:
        """Test that channels table has index on username for lookups."""
        from src.tnse.db.models import Channel

        column = Channel.__table__.columns["username"]
        assert column.index is True

    def test_channels_has_telegram_id_index(self) -> None:
        """Test that channels table has index on telegram_id for lookups."""
        from src.tnse.db.models import Channel

        column = Channel.__table__.columns["telegram_id"]
        assert column.index is True


class TestSearchQueryOptimization:
    """Tests for search query optimization to prevent N+1 patterns."""

    def test_search_query_uses_lateral_join(self) -> None:
        """Test that search query uses LATERAL JOIN for latest metrics."""
        from src.tnse.search.service import SearchService
        import inspect

        source = inspect.getsource(SearchService)

        # The search should use LATERAL JOIN to avoid N+1
        assert "LATERAL" in source

    def test_search_query_joins_all_required_tables(self) -> None:
        """Test that search query JOINs all tables in a single query."""
        from src.tnse.search.service import SearchService
        import inspect

        source = inspect.getsource(SearchService)

        # Should join channels, post_content, and engagement_metrics
        assert "JOIN channels" in source or "join channels" in source.lower()
        assert "JOIN post_content" in source or "join post_content" in source.lower()
        assert "engagement_metrics" in source.lower()

    def test_search_uses_parameterized_queries(self) -> None:
        """Test that search uses parameterized queries to prevent SQL injection."""
        from src.tnse.search.service import SearchService
        import inspect

        source = inspect.getsource(SearchService)

        # Should use parameterized queries with :param_name syntax
        assert ":cutoff_time" in source
        assert ":search_terms" in source
        assert ":limit" in source


class TestRedisUsagePatterns:
    """Tests for Redis usage patterns and key expiry."""

    def test_search_cache_has_ttl(self) -> None:
        """Test that search cache uses TTL for expiry."""
        from src.tnse.search.service import SearchService

        service = SearchService(session_factory=MagicMock())

        # Default cache TTL should be set
        assert hasattr(service, "cache_ttl")
        assert service.cache_ttl > 0

    def test_cache_key_is_deterministic(self) -> None:
        """Test that cache keys are deterministic for the same query."""
        from src.tnse.search.service import SearchService, SearchQuery

        service = SearchService(session_factory=MagicMock())

        query1 = SearchQuery(keywords=["test", "query"], hours=24, limit=100, offset=0)
        query2 = SearchQuery(keywords=["query", "test"], hours=24, limit=100, offset=0)

        key1 = service._build_cache_key(query1)
        key2 = service._build_cache_key(query2)

        # Same keywords (sorted) should produce same key
        assert key1 == key2

    def test_cache_key_differs_for_different_queries(self) -> None:
        """Test that cache keys differ for different queries."""
        from src.tnse.search.service import SearchService, SearchQuery

        service = SearchService(session_factory=MagicMock())

        query1 = SearchQuery(keywords=["test"], hours=24, limit=100, offset=0)
        query2 = SearchQuery(keywords=["test"], hours=12, limit=100, offset=0)

        key1 = service._build_cache_key(query1)
        key2 = service._build_cache_key(query2)

        assert key1 != key2


class TestCeleryTaskPatterns:
    """Tests for Celery task patterns and error handling."""

    def test_collect_all_channels_has_retry_config(self) -> None:
        """Test that collect_all_channels task has retry configuration."""
        from src.tnse.pipeline.tasks import collect_all_channels

        # Task should have max_retries configured
        assert hasattr(collect_all_channels, "max_retries")
        assert collect_all_channels.max_retries >= 1

    def test_collect_channel_content_has_retry_config(self) -> None:
        """Test that collect_channel_content task has retry configuration."""
        from src.tnse.pipeline.tasks import collect_channel_content

        # Task should have max_retries configured
        assert hasattr(collect_channel_content, "max_retries")
        assert collect_channel_content.max_retries >= 1

    def test_celery_app_has_proper_timeouts(self) -> None:
        """Test that Celery app has proper task timeout configuration."""
        from src.tnse.core.celery_app import celery_app

        # Should have task time limits configured
        assert celery_app.conf.task_time_limit is not None
        assert celery_app.conf.task_time_limit > 0

    def test_celery_app_uses_acks_late(self) -> None:
        """Test that Celery uses acks_late for reliability."""
        from src.tnse.core.celery_app import celery_app

        # acks_late ensures message is acknowledged after task completes
        assert celery_app.conf.task_acks_late is True

    def test_celery_app_rejects_on_worker_lost(self) -> None:
        """Test that Celery rejects tasks when worker is lost."""
        from src.tnse.core.celery_app import celery_app

        # Ensures tasks are requeued if worker crashes
        assert celery_app.conf.task_reject_on_worker_lost is True

    def test_celery_beat_schedule_is_configured(self) -> None:
        """Test that Celery Beat schedule is properly configured."""
        from src.tnse.core.celery_app import celery_app

        # Should have periodic tasks scheduled
        assert celery_app.conf.beat_schedule is not None
        assert len(celery_app.conf.beat_schedule) > 0


class TestConnectionPoolConfiguration:
    """Tests for database connection pool configuration."""

    def test_database_settings_generates_valid_url(self) -> None:
        """Test that database settings generate valid connection URLs."""
        from src.tnse.core.config import DatabaseSettings

        settings = DatabaseSettings(
            host="localhost",
            port=5432,
            db="testdb",
            user="testuser",
            password="testpass",
        )

        url = settings.url
        assert "postgresql://" in url
        assert "testuser" in url
        assert "localhost" in url
        assert "testdb" in url

    def test_database_settings_generates_async_url(self) -> None:
        """Test that database settings generate async connection URL."""
        from src.tnse.core.config import DatabaseSettings

        settings = DatabaseSettings(
            host="localhost",
            port=5432,
            db="testdb",
            user="testuser",
            password="testpass",
        )

        async_url = settings.async_url
        assert "postgresql+asyncpg://" in async_url

    def test_redis_settings_generates_valid_url(self) -> None:
        """Test that Redis settings generate valid connection URL."""
        from src.tnse.core.config import RedisSettings

        settings = RedisSettings(
            host="localhost",
            port=6379,
            db=0,
        )

        url = settings.url
        assert "redis://" in url
        assert "localhost" in url
        assert "6379" in url

    def test_redis_settings_supports_tls(self) -> None:
        """Test that Redis settings support TLS connections."""
        from src.tnse.core.config import RedisSettings

        settings = RedisSettings(
            host="localhost",
            port=6379,
            db=0,
            use_tls=True,
        )

        url = settings.url
        assert "rediss://" in url  # Note: rediss with double s for TLS


class TestDatabaseURLParsing:
    """Tests for DATABASE_URL and REDIS_URL parsing (Render.com compatibility)."""

    def test_database_url_parsing(self) -> None:
        """Test that DATABASE_URL is properly parsed."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host:5432/dbname"}):
            from src.tnse.core.config import DatabaseSettings

            # Clear cache if any
            settings = DatabaseSettings()

            assert settings.host == "host"
            assert settings.port == 5432
            assert settings.user == "user"
            assert settings.db == "dbname"

    def test_redis_url_parsing(self) -> None:
        """Test that REDIS_URL is properly parsed."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"REDIS_URL": "redis://:password@host:6379/1"}):
            from src.tnse.core.config import RedisSettings

            settings = RedisSettings()

            assert settings.host == "host"
            assert settings.port == 6379
            assert settings.password == "password"
            assert settings.db == 1

    def test_redis_url_with_tls(self) -> None:
        """Test that rediss:// URL enables TLS."""
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"REDIS_URL": "rediss://host:6379/0"}):
            from src.tnse.core.config import RedisSettings

            settings = RedisSettings()

            assert settings.use_tls is True


class TestAPIResponseModels:
    """Tests for proper API response models using Pydantic v2."""

    def test_health_response_is_json_serializable(self) -> None:
        """Test that health endpoint response is JSON serializable."""
        from src.tnse.main import app
        import json

        client = TestClient(app)
        response = client.get("/health")

        # Should be valid JSON
        data = response.json()
        json_str = json.dumps(data)
        assert len(json_str) > 0

    def test_readiness_response_is_json_serializable(self) -> None:
        """Test that readiness endpoint response is JSON serializable."""
        from src.tnse.main import app
        import json

        client = TestClient(app)

        with patch("src.tnse.main.check_database_connection", return_value=True), \
             patch("src.tnse.main.check_redis_connection", return_value=True):
            response = client.get("/readiness")

        data = response.json()
        json_str = json.dumps(data)
        assert len(json_str) > 0
