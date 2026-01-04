"""
Tests for Post Enrichment Migration (WS-5.2)

These tests verify the Alembic migration for post_enrichments and
llm_usage_logs tables. Since we cannot easily run migrations in unit tests
without a live database, these tests verify:
1. Migration module can be imported
2. Revision chain is correct
3. upgrade/downgrade functions are callable
4. Migration creates expected objects (table names, indexes)
"""

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, call, patch

import pytest


def load_migration_module():
    """Load the migration module directly from file path."""
    migration_path = Path(__file__).parent.parent.parent.parent / "alembic" / "versions" / "b2c3d4e5f6g7_add_post_enrichment_tables.py"
    spec = importlib.util.spec_from_file_location(
        "b2c3d4e5f6g7_add_post_enrichment_tables",
        migration_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrationStructure:
    """Tests for migration file structure and revision chain."""

    def test_migration_module_can_be_imported(self):
        """Test that the migration module can be imported."""
        migration = load_migration_module()

        assert migration is not None

    def test_migration_has_correct_revision(self):
        """Test that migration has correct revision ID."""
        migration = load_migration_module()

        assert migration.revision == "b2c3d4e5f6g7"

    def test_migration_has_correct_down_revision(self):
        """Test that migration points to correct previous revision."""
        migration = load_migration_module()

        assert migration.down_revision == "a1b2c3d4e5f6"

    def test_migration_has_upgrade_function(self):
        """Test that migration has an upgrade function."""
        migration = load_migration_module()

        assert callable(migration.upgrade)

    def test_migration_has_downgrade_function(self):
        """Test that migration has a downgrade function."""
        migration = load_migration_module()

        assert callable(migration.downgrade)


class TestMigrationUpgrade:
    """Tests for migration upgrade operations."""

    def test_upgrade_creates_post_enrichments_table(self):
        """Test that upgrade creates post_enrichments table."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            # Mock create_table to return MagicMock for chaining
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Verify create_table was called for both tables
            create_table_calls = [
                c for c in mock_op.create_table.call_args_list
            ]
            table_names = [c[0][0] for c in create_table_calls]

            assert "post_enrichments" in table_names
            assert "llm_usage_logs" in table_names

    def test_upgrade_creates_llm_usage_logs_table(self):
        """Test that upgrade creates llm_usage_logs table."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Verify llm_usage_logs table was created
            create_table_calls = [c[0][0] for c in mock_op.create_table.call_args_list]
            assert "llm_usage_logs" in create_table_calls

    def test_upgrade_creates_gin_indexes(self):
        """Test that upgrade creates GIN indexes for keyword arrays."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Extract index creation calls
            index_calls = mock_op.create_index.call_args_list
            index_names = [c[0][0] for c in index_calls]

            # Verify GIN indexes are created
            assert "ix_post_enrichments_explicit_keywords_gin" in index_names
            assert "ix_post_enrichments_implicit_keywords_gin" in index_names
            assert "ix_post_enrichments_entities_gin" in index_names

    def test_upgrade_creates_gin_indexes_with_correct_method(self):
        """Test that GIN indexes use postgresql_using='gin'."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Check that GIN indexes use postgresql_using='gin'
            for call_obj in mock_op.create_index.call_args_list:
                index_name = call_obj[0][0]
                if "_gin" in index_name:
                    kwargs = call_obj[1]
                    assert "postgresql_using" in kwargs
                    assert kwargs["postgresql_using"] == "gin"


class TestMigrationDowngrade:
    """Tests for migration downgrade operations."""

    def test_downgrade_drops_post_enrichments_table(self):
        """Test that downgrade drops post_enrichments table."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            migration.downgrade()

            # Verify drop_table was called for post_enrichments
            drop_table_calls = [c[0][0] for c in mock_op.drop_table.call_args_list]
            assert "post_enrichments" in drop_table_calls

    def test_downgrade_drops_llm_usage_logs_table(self):
        """Test that downgrade drops llm_usage_logs table."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            migration.downgrade()

            # Verify drop_table was called for llm_usage_logs
            drop_table_calls = [c[0][0] for c in mock_op.drop_table.call_args_list]
            assert "llm_usage_logs" in drop_table_calls

    def test_downgrade_drops_indexes_before_tables(self):
        """Test that downgrade drops indexes before tables."""
        migration = load_migration_module()

        call_order = []

        def track_drop_index(*args, **kwargs):
            call_order.append(("drop_index", args[0]))

        def track_drop_table(*args, **kwargs):
            call_order.append(("drop_table", args[0]))

        with patch.object(migration, "op") as mock_op:
            mock_op.drop_index.side_effect = track_drop_index
            mock_op.drop_table.side_effect = track_drop_table

            migration.downgrade()

            # Find the position of post_enrichments table drop
            table_drop_positions = [
                i for i, (op_type, name) in enumerate(call_order)
                if op_type == "drop_table" and name == "post_enrichments"
            ]

            # Find positions of GIN index drops
            gin_index_positions = [
                i for i, (op_type, name) in enumerate(call_order)
                if op_type == "drop_index" and "_gin" in name
            ]

            # Verify all GIN indexes are dropped before the table
            if table_drop_positions and gin_index_positions:
                table_pos = table_drop_positions[0]
                for idx_pos in gin_index_positions:
                    assert idx_pos < table_pos, "GIN indexes should be dropped before the table"

    def test_downgrade_drops_all_gin_indexes(self):
        """Test that downgrade drops all GIN indexes."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            migration.downgrade()

            # Extract dropped indexes
            dropped_indexes = [c[0][0] for c in mock_op.drop_index.call_args_list]

            # Verify all GIN indexes are dropped
            assert "ix_post_enrichments_explicit_keywords_gin" in dropped_indexes
            assert "ix_post_enrichments_implicit_keywords_gin" in dropped_indexes
            assert "ix_post_enrichments_entities_gin" in dropped_indexes


class TestMigrationTableStructure:
    """Tests for expected table column structure in migration."""

    def test_post_enrichments_has_required_columns(self):
        """Test that post_enrichments table creation includes required columns."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Find the post_enrichments create_table call
            for call_obj in mock_op.create_table.call_args_list:
                if call_obj[0][0] == "post_enrichments":
                    # Get all column definitions (args after table name)
                    columns = [arg for arg in call_obj[0][1:]]
                    column_names = [col.name for col in columns if hasattr(col, "name")]

                    # Verify required columns are present
                    expected_columns = [
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
                    for col in expected_columns:
                        assert col in column_names, f"Missing column: {col}"
                    break
            else:
                pytest.fail("post_enrichments table not found in create_table calls")

    def test_llm_usage_logs_has_required_columns(self):
        """Test that llm_usage_logs table creation includes required columns."""
        migration = load_migration_module()

        with patch.object(migration, "op") as mock_op:
            mock_op.create_table.return_value = MagicMock()
            mock_op.create_index.return_value = MagicMock()

            migration.upgrade()

            # Find the llm_usage_logs create_table call
            for call_obj in mock_op.create_table.call_args_list:
                if call_obj[0][0] == "llm_usage_logs":
                    # Get all column definitions (args after table name)
                    columns = [arg for arg in call_obj[0][1:]]
                    column_names = [col.name for col in columns if hasattr(col, "name")]

                    # Verify required columns are present
                    expected_columns = [
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
                    for col in expected_columns:
                        assert col in column_names, f"Missing column: {col}"
                    break
            else:
                pytest.fail("llm_usage_logs table not found in create_table calls")
