"""
Tests for health check endpoints.

Following TDD methodology: these tests validate health and readiness endpoints
for Render.com deployment requirements.

Work Stream: WS-4.1 - Render.com Configuration
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the basic health check endpoint."""

    def test_health_endpoint_returns_ok(self):
        """Test that /health returns a successful response."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    def test_health_endpoint_returns_json(self):
        """Test that /health returns JSON content type."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"


class TestReadinessEndpoint:
    """Tests for the readiness probe endpoint for Render.com."""

    def test_readiness_endpoint_exists(self):
        """Test that /readiness endpoint exists."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/readiness")

        # Should not be 404
        assert response.status_code != 404

    def test_readiness_returns_service_status(self):
        """Test that /readiness returns status of dependent services."""
        from src.tnse.main import app

        client = TestClient(app)

        with patch("src.tnse.main.check_database_connection") as mock_db, \
             patch("src.tnse.main.check_redis_connection") as mock_redis:
            mock_db.return_value = True
            mock_redis.return_value = True

            response = client.get("/readiness")
            data = response.json()

            assert response.status_code == 200
            assert "status" in data
            assert "services" in data
            assert "database" in data["services"]
            assert "redis" in data["services"]

    def test_readiness_returns_503_when_database_down(self):
        """Test that /readiness returns 503 when database is not available."""
        from src.tnse.main import app

        client = TestClient(app)

        with patch("src.tnse.main.check_database_connection") as mock_db, \
             patch("src.tnse.main.check_redis_connection") as mock_redis:
            mock_db.return_value = False
            mock_redis.return_value = True

            response = client.get("/readiness")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["database"] is False

    def test_readiness_returns_503_when_redis_down(self):
        """Test that /readiness returns 503 when Redis is not available."""
        from src.tnse.main import app

        client = TestClient(app)

        with patch("src.tnse.main.check_database_connection") as mock_db, \
             patch("src.tnse.main.check_redis_connection") as mock_redis:
            mock_db.return_value = True
            mock_redis.return_value = False

            response = client.get("/readiness")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["services"]["redis"] is False

    def test_readiness_healthy_when_all_services_up(self):
        """Test that /readiness returns healthy when all services are available."""
        from src.tnse.main import app

        client = TestClient(app)

        with patch("src.tnse.main.check_database_connection") as mock_db, \
             patch("src.tnse.main.check_redis_connection") as mock_redis:
            mock_db.return_value = True
            mock_redis.return_value = True

            response = client.get("/readiness")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["database"] is True
            assert data["services"]["redis"] is True


class TestLivenessEndpoint:
    """Tests for the liveness probe endpoint."""

    def test_liveness_endpoint_exists(self):
        """Test that /liveness endpoint exists."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/liveness")

        assert response.status_code != 404

    def test_liveness_returns_ok_always(self):
        """Test that /liveness always returns OK if the app is running."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/liveness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_endpoint_returns_api_info(self):
        """Test that / returns API information."""
        from src.tnse.main import app

        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "health" in data


class TestCheckDatabaseConnection:
    """Tests for the database connection check function."""

    def test_check_database_connection_returns_true_on_success(self):
        """Test that check_database_connection returns True on successful connection."""
        with patch("src.tnse.main.get_database_engine") as mock_get_engine:
            mock_engine = MagicMock()
            mock_connection = MagicMock()
            mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
            mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_get_engine.return_value = mock_engine

            from src.tnse.main import check_database_connection

            result = check_database_connection()
            assert result is True

    def test_check_database_connection_returns_false_on_error(self):
        """Test that check_database_connection returns False on connection error."""
        with patch("src.tnse.main.get_database_engine") as mock_get_engine:
            mock_get_engine.side_effect = Exception("Connection failed")

            from src.tnse.main import check_database_connection

            result = check_database_connection()
            assert result is False


class TestCheckRedisConnection:
    """Tests for the Redis connection check function."""

    def test_check_redis_connection_returns_true_on_success(self):
        """Test that check_redis_connection returns True on successful ping."""
        with patch("src.tnse.main.get_redis_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_get_client.return_value = mock_client

            from src.tnse.main import check_redis_connection

            result = check_redis_connection()
            assert result is True

    def test_check_redis_connection_returns_false_on_error(self):
        """Test that check_redis_connection returns False on connection error."""
        with patch("src.tnse.main.get_redis_client") as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            from src.tnse.main import check_redis_connection

            result = check_redis_connection()
            assert result is False
