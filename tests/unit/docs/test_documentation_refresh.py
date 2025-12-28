"""
Tests for documentation refresh (WS-6.6).

These tests validate that all documentation reflects the current state
of the codebase after the Phase 6 modernization.
"""

import re
from pathlib import Path


# Get project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class TestClaudeMd:
    """Tests for CLAUDE.md documentation updates."""

    def test_claude_md_exists(self) -> None:
        """CLAUDE.md should exist in project root."""
        claude_md_path = PROJECT_ROOT / "CLAUDE.md"
        assert claude_md_path.exists(), "CLAUDE.md not found in project root"

    def test_claude_md_specifies_python_312(self) -> None:
        """CLAUDE.md should specify Python 3.12+ as requirement."""
        claude_md_path = PROJECT_ROOT / "CLAUDE.md"
        content = claude_md_path.read_text()
        # Should mention Python 3.12 or higher
        assert re.search(r"Python\s+3\.12\+?", content, re.IGNORECASE), (
            "CLAUDE.md should specify Python 3.12+ as minimum version"
        )

    def test_claude_md_documents_modern_typing(self) -> None:
        """CLAUDE.md should document modern typing patterns (X | None vs Optional)."""
        claude_md_path = PROJECT_ROOT / "CLAUDE.md"
        content = claude_md_path.read_text()
        # Should mention union syntax or modern typing
        has_union_mention = "| None" in content or "union" in content.lower()
        assert has_union_mention, (
            "CLAUDE.md should document modern union typing syntax (X | None)"
        )

    def test_claude_md_documents_match_case(self) -> None:
        """CLAUDE.md should mention match/case pattern matching if used."""
        claude_md_path = PROJECT_ROOT / "CLAUDE.md"
        content = claude_md_path.read_text()
        # Should mention match/case or pattern matching
        has_match_mention = "match" in content.lower() and "case" in content.lower()
        assert has_match_mention, (
            "CLAUDE.md should document match/case pattern matching"
        )

    def test_claude_md_documents_type_alias(self) -> None:
        """CLAUDE.md should document TypeAlias usage."""
        claude_md_path = PROJECT_ROOT / "CLAUDE.md"
        content = claude_md_path.read_text()
        # Should mention TypeAlias
        assert "TypeAlias" in content, (
            "CLAUDE.md should document TypeAlias usage for type definitions"
        )


class TestReadmeMd:
    """Tests for README.md documentation updates."""

    def test_readme_exists(self) -> None:
        """README.md should exist in project root."""
        readme_path = PROJECT_ROOT / "README.md"
        assert readme_path.exists(), "README.md not found in project root"

    def test_readme_specifies_python_312(self) -> None:
        """README.md should specify Python 3.12+ as requirement."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text()
        # Should mention Python 3.12 or higher
        assert re.search(r"Python\s+3\.12\+?", content, re.IGNORECASE), (
            "README.md should specify Python 3.12+ as minimum version"
        )

    def test_readme_specifies_postgresql_version(self) -> None:
        """README.md should specify PostgreSQL version requirement."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text()
        # Should mention PostgreSQL version
        assert re.search(r"PostgreSQL\s+\d+", content, re.IGNORECASE), (
            "README.md should specify PostgreSQL version requirement"
        )

    def test_readme_specifies_redis_version(self) -> None:
        """README.md should specify Redis version requirement."""
        readme_path = PROJECT_ROOT / "README.md"
        content = readme_path.read_text()
        # Should mention Redis version (6+)
        assert re.search(r"Redis\s+\d+", content, re.IGNORECASE), (
            "README.md should specify Redis version requirement"
        )


class TestDeploymentMd:
    """Tests for DEPLOYMENT.md documentation updates."""

    def test_deployment_md_exists(self) -> None:
        """DEPLOYMENT.md should exist in docs directory."""
        deployment_path = PROJECT_ROOT / "docs" / "DEPLOYMENT.md"
        assert deployment_path.exists(), "DEPLOYMENT.md not found in docs/"

    def test_deployment_specifies_python_312(self) -> None:
        """DEPLOYMENT.md should specify Python 3.12+ as requirement."""
        deployment_path = PROJECT_ROOT / "docs" / "DEPLOYMENT.md"
        content = deployment_path.read_text()
        # Should mention Python 3.12 or higher
        assert re.search(r"Python\s+3\.12", content, re.IGNORECASE), (
            "DEPLOYMENT.md should specify Python 3.12 as minimum version"
        )

    def test_deployment_specifies_postgresql_14(self) -> None:
        """DEPLOYMENT.md should specify PostgreSQL 14+ as requirement."""
        deployment_path = PROJECT_ROOT / "docs" / "DEPLOYMENT.md"
        content = deployment_path.read_text()
        # Should mention PostgreSQL 14 or higher
        assert re.search(r"PostgreSQL\s+14", content, re.IGNORECASE), (
            "DEPLOYMENT.md should specify PostgreSQL 14 as minimum version"
        )


class TestChangelogMd:
    """Tests for CHANGELOG.md existence and content."""

    def test_changelog_exists(self) -> None:
        """CHANGELOG.md should exist in project root."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        assert changelog_path.exists(), "CHANGELOG.md not found in project root"

    def test_changelog_has_version_020(self) -> None:
        """CHANGELOG.md should document version 0.2.0 modernization."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        content = changelog_path.read_text()
        # Should have entry for version 0.2.0 (the modernization release)
        assert "0.2.0" in content, (
            "CHANGELOG.md should document version 0.2.0 (modernization release)"
        )

    def test_changelog_documents_python_312_requirement(self) -> None:
        """CHANGELOG.md should document Python 3.12 requirement change."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        content = changelog_path.read_text()
        # Should mention Python version change
        has_python_mention = (
            "Python 3.12" in content or
            "python 3.12" in content.lower() or
            "Python version" in content
        )
        assert has_python_mention, (
            "CHANGELOG.md should document Python 3.12 requirement change"
        )

    def test_changelog_documents_dependency_updates(self) -> None:
        """CHANGELOG.md should mention dependency updates."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        content = changelog_path.read_text()
        # Should mention dependencies or updates
        has_deps_mention = (
            "depend" in content.lower() or
            "update" in content.lower() or
            "upgrade" in content.lower()
        )
        assert has_deps_mention, (
            "CHANGELOG.md should document dependency updates"
        )

    def test_changelog_documents_breaking_changes(self) -> None:
        """CHANGELOG.md should document breaking changes if any."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        content = changelog_path.read_text()
        # Should mention breaking changes section or note there are none
        has_breaking = (
            "breaking" in content.lower() or
            "BREAKING" in content or
            "migration" in content.lower()
        )
        assert has_breaking, (
            "CHANGELOG.md should mention breaking changes or migration notes"
        )


class TestRequirementsDocumentation:
    """Tests for requirements documentation accuracy."""

    def test_requirements_txt_has_modern_versions(self) -> None:
        """requirements.txt should have December 2025 versions documented."""
        requirements_path = PROJECT_ROOT / "requirements.txt"
        content = requirements_path.read_text()
        # Should have version header comment
        assert "December 2025" in content or "WS-6.1" in content, (
            "requirements.txt should be documented as December 2025 versions"
        )

    def test_requirements_dev_txt_has_modern_versions(self) -> None:
        """requirements-dev.txt should have December 2025 versions documented."""
        requirements_dev_path = PROJECT_ROOT / "requirements-dev.txt"
        content = requirements_dev_path.read_text()
        # Should have version header comment
        assert "December 2025" in content or "WS-6.1" in content, (
            "requirements-dev.txt should be documented as December 2025 versions"
        )

    def test_pyproject_toml_version_020(self) -> None:
        """pyproject.toml should have version 0.2.0."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'version = "0.2.0"' in content, (
            "pyproject.toml should have version 0.2.0"
        )

    def test_pyproject_requires_python_312(self) -> None:
        """pyproject.toml should require Python 3.12+."""
        pyproject_path = PROJECT_ROOT / "pyproject.toml"
        content = pyproject_path.read_text()
        assert 'requires-python = ">=3.12"' in content, (
            "pyproject.toml should require Python >= 3.12"
        )


class TestDocumentationConsistency:
    """Tests for documentation consistency across files."""

    def test_python_version_consistent(self) -> None:
        """Python version should be consistent across all docs."""
        claude_md = (PROJECT_ROOT / "CLAUDE.md").read_text()
        readme_md = (PROJECT_ROOT / "README.md").read_text()
        deployment_md = (PROJECT_ROOT / "docs" / "DEPLOYMENT.md").read_text()

        # All should mention 3.12+
        has_312_claude = re.search(r"Python\s+3\.12", claude_md, re.IGNORECASE)
        has_312_readme = re.search(r"Python\s+3\.12", readme_md, re.IGNORECASE)
        has_312_deploy = re.search(r"Python\s+3\.12", deployment_md, re.IGNORECASE)

        assert has_312_claude and has_312_readme and has_312_deploy, (
            "Python 3.12+ should be mentioned consistently in all documentation"
        )

    def test_modernization_phase_documented(self) -> None:
        """Phase 6 modernization should be documented somewhere."""
        changelog_path = PROJECT_ROOT / "CHANGELOG.md"
        if changelog_path.exists():
            content = changelog_path.read_text()
            has_modernization = (
                "modernization" in content.lower() or
                "phase 6" in content.lower() or
                "WS-6" in content
            )
            assert has_modernization, (
                "CHANGELOG.md should document Phase 6 modernization"
            )
        else:
            # Will fail in test_changelog_exists first
            pass
