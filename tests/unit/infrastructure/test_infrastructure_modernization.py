# =============================================================================
# TNSE - Telegram News Search Engine
# Infrastructure Modernization Tests (WS-6.5)
#
# These tests verify that infrastructure files (Dockerfile, docker-compose,
# CI/CD workflows, render.yaml, Makefile) are updated to latest practices
# for December 2025.
# =============================================================================

"""Tests for infrastructure modernization (WS-6.5)."""

import re
from pathlib import Path

import pytest
import yaml


# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestDockerfileModernization:
    """Tests for Dockerfile modernization."""

    @pytest.fixture
    def dockerfile_content(self) -> str:
        """Read Dockerfile content."""
        dockerfile_path = PROJECT_ROOT / "Dockerfile"
        return dockerfile_path.read_text()

    def test_base_image_is_python_312_or_higher(self, dockerfile_content: str) -> None:
        """Dockerfile should use Python 3.12+ base image.

        Python 3.12 is the minimum version specified in pyproject.toml
        after WS-6.3 modernization. The Docker image should match.
        """
        # Match FROM python:3.XX-slim pattern
        base_image_pattern = r"FROM python:(\d+\.\d+)-slim"
        match = re.search(base_image_pattern, dockerfile_content)

        assert match is not None, "Could not find Python base image in Dockerfile"

        version_string = match.group(1)
        major, minor = map(int, version_string.split("."))

        assert major >= 3, f"Python major version should be 3, got {major}"
        assert minor >= 12, f"Python minor version should be 12 or higher, got {minor}"

    def test_multi_stage_build_has_optimized_layers(
        self, dockerfile_content: str
    ) -> None:
        """Dockerfile should have optimized layer ordering.

        Requirements should be copied before source code for better
        Docker layer caching. This allows rebuilds to skip dependency
        installation when only source code changes.
        """
        # Check that requirements are copied before source
        requirements_copy_pos = dockerfile_content.find("COPY requirements")
        src_copy_pos = dockerfile_content.find("COPY src/")

        assert requirements_copy_pos > 0, "Requirements COPY not found"
        assert src_copy_pos > 0, "Source COPY not found"
        assert requirements_copy_pos < src_copy_pos, (
            "Requirements should be copied before source for optimal caching"
        )

    def test_production_stage_uses_non_root_user(
        self, dockerfile_content: str
    ) -> None:
        """Production stage should use non-root user for security."""
        assert "USER appuser" in dockerfile_content or "USER app" in dockerfile_content, (
            "Production Dockerfile should run as non-root user"
        )

    def test_health_check_is_configured(self, dockerfile_content: str) -> None:
        """Dockerfile should have HEALTHCHECK instruction."""
        assert "HEALTHCHECK" in dockerfile_content, (
            "Dockerfile should include HEALTHCHECK instruction"
        )

    def test_no_deprecated_maintainer_instruction(
        self, dockerfile_content: str
    ) -> None:
        """Dockerfile should not use deprecated MAINTAINER instruction.

        MAINTAINER is deprecated in favor of LABEL maintainer="..."
        """
        lines = dockerfile_content.split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("MAINTAINER"):
                pytest.fail("MAINTAINER instruction is deprecated, use LABEL instead")


class TestDockerComposeModernization:
    """Tests for docker-compose.yml modernization."""

    @pytest.fixture
    def compose_content(self) -> dict:
        """Parse docker-compose.yml content."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        return yaml.safe_load(compose_path.read_text())

    @pytest.fixture
    def compose_raw(self) -> str:
        """Read raw docker-compose.yml content."""
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        return compose_path.read_text()

    def test_compose_v2_syntax_no_version_key(self, compose_content: dict) -> None:
        """docker-compose.yml should use Compose V2 syntax (no version key).

        Docker Compose V2 does not require a version key at the top of
        the file. Removing it is recommended for Compose V2 compatibility.
        """
        assert "version" not in compose_content, (
            "docker-compose.yml should not have 'version' key (Compose V2 syntax)"
        )

    def test_postgres_image_is_current(self, compose_content: dict) -> None:
        """PostgreSQL image should be version 16 or higher.

        PostgreSQL 16 is the current stable version as of December 2025.
        It includes performance improvements and new features.
        """
        postgres_service = compose_content.get("services", {}).get("postgres", {})
        image = postgres_service.get("image", "")

        # Match postgres:XX-alpine pattern
        match = re.match(r"postgres:(\d+)", image)
        assert match is not None, f"Could not parse PostgreSQL version from: {image}"

        version = int(match.group(1))
        assert version >= 16, f"PostgreSQL should be version 16+, got {version}"

    def test_redis_image_is_current(self, compose_content: dict) -> None:
        """Redis image should be version 7 or higher.

        Redis 7 is the current stable version with improved performance.
        """
        redis_service = compose_content.get("services", {}).get("redis", {})
        image = redis_service.get("image", "")

        # Match redis:X-alpine pattern
        match = re.match(r"redis:(\d+)", image)
        assert match is not None, f"Could not parse Redis version from: {image}"

        version = int(match.group(1))
        assert version >= 7, f"Redis should be version 7+, got {version}"

    def test_services_use_healthchecks(self, compose_content: dict) -> None:
        """All critical services should have healthcheck configured."""
        services = compose_content.get("services", {})

        required_healthchecks = ["postgres", "redis"]
        for service_name in required_healthchecks:
            service = services.get(service_name, {})
            assert "healthcheck" in service, (
                f"Service '{service_name}' should have healthcheck configured"
            )

    def test_named_volumes_used(self, compose_content: dict) -> None:
        """Docker Compose should use named volumes for persistence."""
        volumes = compose_content.get("volumes", {})
        assert len(volumes) > 0, "Docker Compose should define named volumes"

        # Check for postgres and redis data volumes
        assert "postgres_data" in volumes, "postgres_data volume should be defined"
        assert "redis_data" in volumes, "redis_data volume should be defined"


class TestGitHubActionsModernization:
    """Tests for GitHub Actions workflow modernization."""

    @pytest.fixture
    def ci_workflow_content(self) -> dict:
        """Parse CI workflow content."""
        ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
        return yaml.safe_load(ci_path.read_text())

    def test_actions_checkout_v4(self, ci_workflow_content: dict) -> None:
        """GitHub Actions should use actions/checkout@v4."""
        jobs = ci_workflow_content.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                uses = step.get("uses", "")
                if "actions/checkout" in uses:
                    version = uses.split("@")[1] if "@" in uses else ""
                    assert version == "v4", (
                        f"Job '{job_name}' should use actions/checkout@v4, got {uses}"
                    )

    def test_actions_setup_python_v5(self, ci_workflow_content: dict) -> None:
        """GitHub Actions should use actions/setup-python@v5."""
        jobs = ci_workflow_content.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                uses = step.get("uses", "")
                if "actions/setup-python" in uses:
                    version = uses.split("@")[1] if "@" in uses else ""
                    assert version == "v5", (
                        f"Job '{job_name}' should use actions/setup-python@v5, got {uses}"
                    )

    def test_actions_cache_v4(self, ci_workflow_content: dict) -> None:
        """GitHub Actions should use actions/cache@v4."""
        jobs = ci_workflow_content.get("jobs", {})

        for job_name, job_config in jobs.items():
            steps = job_config.get("steps", [])
            for step in steps:
                uses = step.get("uses", "")
                if "actions/cache" in uses:
                    version = uses.split("@")[1] if "@" in uses else ""
                    assert version == "v4", (
                        f"Job '{job_name}' should use actions/cache@v4, got {uses}"
                    )

    def test_python_version_is_312_or_higher(
        self, ci_workflow_content: dict
    ) -> None:
        """CI should test with Python 3.12 or higher."""
        env_vars = ci_workflow_content.get("env", {})
        python_version = env_vars.get("PYTHON_VERSION", "")

        if python_version:
            major, minor = map(int, python_version.split("."))
            assert major >= 3 and minor >= 12, (
                f"Python version should be 3.12+, got {python_version}"
            )

    def test_uses_docker_buildx_v3(self, ci_workflow_content: dict) -> None:
        """Docker build job should use docker/setup-buildx-action@v3."""
        docker_job = ci_workflow_content.get("jobs", {}).get("docker-build", {})
        steps = docker_job.get("steps", [])

        for step in steps:
            uses = step.get("uses", "")
            if "docker/setup-buildx-action" in uses:
                version = uses.split("@")[1] if "@" in uses else ""
                assert version == "v3", (
                    f"Should use docker/setup-buildx-action@v3, got {uses}"
                )

    def test_uses_docker_build_push_v6(self, ci_workflow_content: dict) -> None:
        """Docker build job should use docker/build-push-action@v6."""
        docker_job = ci_workflow_content.get("jobs", {}).get("docker-build", {})
        steps = docker_job.get("steps", [])

        for step in steps:
            uses = step.get("uses", "")
            if "docker/build-push-action" in uses:
                version = uses.split("@")[1] if "@" in uses else ""
                assert version == "v6", (
                    f"Should use docker/build-push-action@v6, got {uses}"
                )

    def test_postgres_service_version_16(self, ci_workflow_content: dict) -> None:
        """CI test job should use PostgreSQL 16 service."""
        test_job = ci_workflow_content.get("jobs", {}).get("test", {})
        services = test_job.get("services", {})
        postgres = services.get("postgres", {})
        image = postgres.get("image", "")

        assert "postgres:16" in image, (
            f"CI should use postgres:16, got {image}"
        )

    def test_redis_service_version_7(self, ci_workflow_content: dict) -> None:
        """CI test job should use Redis 7 service."""
        test_job = ci_workflow_content.get("jobs", {}).get("test", {})
        services = test_job.get("services", {})
        redis = services.get("redis", {})
        image = redis.get("image", "")

        assert "redis:7" in image, (
            f"CI should use redis:7, got {image}"
        )


class TestRenderYamlModernization:
    """Tests for Render.com configuration modernization."""

    @pytest.fixture
    def render_content(self) -> dict:
        """Parse render.yaml content."""
        render_path = PROJECT_ROOT / "render.yaml"
        return yaml.safe_load(render_path.read_text())

    def test_render_yaml_exists(self) -> None:
        """Render.yaml should exist in project root."""
        render_path = PROJECT_ROOT / "render.yaml"
        assert render_path.exists(), "render.yaml should exist"

    def test_all_services_have_auto_deploy(self, render_content: dict) -> None:
        """All Render services should have autoDeploy configured."""
        services = render_content.get("services", [])

        for service in services:
            if service.get("type") in ("web", "worker"):
                service_name = service.get("name", "unknown")
                assert "autoDeploy" in service, (
                    f"Service '{service_name}' should have autoDeploy configured"
                )

    def test_health_check_configured_for_web_service(
        self, render_content: dict
    ) -> None:
        """Web service should have health check path configured."""
        services = render_content.get("services", [])

        web_services = [s for s in services if s.get("type") == "web"]
        for service in web_services:
            assert "healthCheckPath" in service, (
                f"Web service '{service.get('name')}' should have healthCheckPath"
            )


class TestMakefileModernization:
    """Tests for Makefile modernization."""

    @pytest.fixture
    def makefile_content(self) -> str:
        """Read Makefile content."""
        makefile_path = PROJECT_ROOT / "Makefile"
        return makefile_path.read_text()

    def test_docker_compose_v2_command(self, makefile_content: str) -> None:
        """Makefile should use 'docker compose' (V2) instead of 'docker-compose'."""
        assert "DOCKER_COMPOSE := docker compose" in makefile_content, (
            "Makefile should use 'docker compose' (V2 syntax)"
        )

    def test_essential_targets_exist(self, makefile_content: str) -> None:
        """Makefile should have all essential targets."""
        essential_targets = [
            "help",
            "install",
            "install-dev",
            "setup",
            "clean",
            "lint",
            "format",
            "type-check",
            "test",
            "test-cov",
            "docker-up",
            "docker-down",
            "docker-build",
            "db-upgrade",
            "run",
            "run-dev",
            "ci",
        ]

        for target in essential_targets:
            assert f"{target}:" in makefile_content, (
                f"Makefile should have '{target}' target"
            )

    def test_ci_target_includes_all_checks(self, makefile_content: str) -> None:
        """CI target should include lint, type-check, and test."""
        # Find CI target line
        ci_pattern = r"ci:.*lint.*type-check.*test"
        assert re.search(ci_pattern, makefile_content), (
            "CI target should include lint, type-check, and test"
        )
