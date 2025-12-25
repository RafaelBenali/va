"""
TNSE Export Service Tests

Unit tests for the export functionality that generates CSV and JSON files
from search results.

Work Stream: WS-2.5 - Export Functionality

Requirements addressed:
- REQ-RP-005: System MUST support export to CSV, JSON, and formatted text
- REQ-RP-001: System MUST display ranked news list with direct Telegram links
- REQ-RP-002: System SHALL show engagement metrics for each item
"""

import csv
import io
import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.tnse.search.service import SearchResult


def create_sample_search_result(
    channel_username: str = "test_channel",
    channel_title: str = "Test Channel",
    text_content: str = "This is test content about corruption",
    view_count: int = 1000,
    reaction_score: float = 50.0,
    relative_engagement: float = 0.05,
    telegram_message_id: int = 123,
    published_at: datetime = None,
) -> SearchResult:
    """Helper function to create sample SearchResult objects."""
    return SearchResult(
        post_id=str(uuid4()),
        channel_id=str(uuid4()),
        channel_username=channel_username,
        channel_title=channel_title,
        text_content=text_content,
        published_at=published_at or datetime.now(timezone.utc),
        view_count=view_count,
        reaction_score=reaction_score,
        relative_engagement=relative_engagement,
        telegram_message_id=telegram_message_id,
    )


class TestExportServiceInstantiation:
    """Tests for ExportService instantiation."""

    def test_export_service_can_be_imported(self) -> None:
        """Test that ExportService can be imported."""
        from src.tnse.export.service import ExportService

        assert ExportService is not None

    def test_export_service_can_be_instantiated(self) -> None:
        """Test that ExportService can be instantiated."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        assert service is not None


class TestExportToCSV:
    """Tests for CSV export functionality."""

    def test_export_to_csv_returns_string(self) -> None:
        """Test that export_to_csv returns a string."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        csv_output = service.export_to_csv(results)

        assert isinstance(csv_output, str)

    def test_export_to_csv_empty_results_returns_header_only(self) -> None:
        """Test that empty results returns CSV with header only."""
        from src.tnse.export.service import ExportService

        service = ExportService()

        csv_output = service.export_to_csv([])

        # Should have header row
        assert csv_output.strip() != ""
        reader = csv.reader(io.StringIO(csv_output))
        rows = list(reader)
        assert len(rows) == 1  # Header only

    def test_export_to_csv_includes_required_columns(self) -> None:
        """Test that CSV includes all required columns."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        fieldnames = reader.fieldnames

        required_columns = [
            "channel_username",
            "channel_title",
            "text_preview",
            "view_count",
            "reaction_score",
            "relative_engagement",
            "published_at",
            "telegram_link",
        ]

        for column in required_columns:
            assert column in fieldnames, f"Missing required column: {column}"

    def test_export_to_csv_includes_telegram_link(self) -> None:
        """Test that CSV includes Telegram deep link."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                channel_username="news_channel",
                telegram_message_id=456,
            )
        ]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        row = next(reader)

        assert row["telegram_link"] == "https://t.me/news_channel/456"

    def test_export_to_csv_includes_all_results(self) -> None:
        """Test that CSV includes all search results."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(channel_username="channel1"),
            create_sample_search_result(channel_username="channel2"),
            create_sample_search_result(channel_username="channel3"),
        ]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        rows = list(reader)

        assert len(rows) == 3

    def test_export_to_csv_handles_special_characters(self) -> None:
        """Test that CSV properly escapes special characters."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                text_content='Text with "quotes" and, commas',
            )
        ]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        row = next(reader)

        assert '"quotes"' in row["text_preview"] or "quotes" in row["text_preview"]

    def test_export_to_csv_handles_cyrillic_text(self) -> None:
        """Test that CSV properly handles Russian/Cyrillic text."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                text_content="Новости о коррупции в политике",
                channel_title="Новостной канал",
            )
        ]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        row = next(reader)

        assert "коррупции" in row["text_preview"]
        assert "Новостной канал" in row["channel_title"]

    def test_export_to_csv_truncates_long_text(self) -> None:
        """Test that long text content is truncated in preview."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        long_text = "A" * 500
        results = [create_sample_search_result(text_content=long_text)]

        csv_output = service.export_to_csv(results)

        reader = csv.DictReader(io.StringIO(csv_output))
        row = next(reader)

        # Preview should be truncated
        assert len(row["text_preview"]) <= 203  # 200 chars + "..."


class TestExportToJSON:
    """Tests for JSON export functionality."""

    def test_export_to_json_returns_string(self) -> None:
        """Test that export_to_json returns a string."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_output = service.export_to_json(results)

        assert isinstance(json_output, str)

    def test_export_to_json_is_valid_json(self) -> None:
        """Test that export_to_json returns valid JSON."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_output = service.export_to_json(results)

        # Should parse without error
        parsed = json.loads(json_output)
        assert parsed is not None

    def test_export_to_json_empty_results_returns_empty_array(self) -> None:
        """Test that empty results returns empty JSON array."""
        from src.tnse.export.service import ExportService

        service = ExportService()

        json_output = service.export_to_json([])

        parsed = json.loads(json_output)
        assert parsed == {"results": [], "total": 0, "exported_at": parsed["exported_at"]}

    def test_export_to_json_includes_required_fields(self) -> None:
        """Test that JSON includes all required fields."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)
        result = parsed["results"][0]

        required_fields = [
            "post_id",
            "channel_username",
            "channel_title",
            "text_content",
            "text_preview",
            "view_count",
            "reaction_score",
            "relative_engagement",
            "published_at",
            "telegram_link",
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    def test_export_to_json_includes_telegram_link(self) -> None:
        """Test that JSON includes Telegram deep link."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                channel_username="news_channel",
                telegram_message_id=789,
            )
        ]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)
        result = parsed["results"][0]

        assert result["telegram_link"] == "https://t.me/news_channel/789"

    def test_export_to_json_includes_all_results(self) -> None:
        """Test that JSON includes all search results."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(channel_username="channel1"),
            create_sample_search_result(channel_username="channel2"),
            create_sample_search_result(channel_username="channel3"),
        ]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)
        assert len(parsed["results"]) == 3
        assert parsed["total"] == 3

    def test_export_to_json_includes_metadata(self) -> None:
        """Test that JSON includes export metadata."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)

        assert "total" in parsed
        assert "exported_at" in parsed
        assert "results" in parsed

    def test_export_to_json_handles_cyrillic_text(self) -> None:
        """Test that JSON properly handles Russian/Cyrillic text."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                text_content="Новости о коррупции в политике",
                channel_title="Новостной канал",
            )
        ]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)
        result = parsed["results"][0]

        assert "коррупции" in result["text_content"]
        assert "Новостной канал" in result["channel_title"]

    def test_export_to_json_uses_iso_format_for_dates(self) -> None:
        """Test that JSON uses ISO format for datetime fields."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        test_time = datetime(2025, 12, 26, 10, 30, 0, tzinfo=timezone.utc)
        results = [create_sample_search_result(published_at=test_time)]

        json_output = service.export_to_json(results)

        parsed = json.loads(json_output)
        result = parsed["results"][0]

        # Should be ISO format string
        assert "2025-12-26" in result["published_at"]
        assert "10:30:00" in result["published_at"]


class TestExportToBytes:
    """Tests for exporting to bytes for file transmission."""

    def test_export_to_csv_bytes_returns_bytes(self) -> None:
        """Test that export_to_csv_bytes returns bytes."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        csv_bytes = service.export_to_csv_bytes(results)

        assert isinstance(csv_bytes, bytes)

    def test_export_to_json_bytes_returns_bytes(self) -> None:
        """Test that export_to_json_bytes returns bytes."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_bytes = service.export_to_json_bytes(results)

        assert isinstance(json_bytes, bytes)

    def test_export_to_csv_bytes_is_utf8_encoded(self) -> None:
        """Test that CSV bytes are UTF-8 encoded."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                text_content="Русский текст",
            )
        ]

        csv_bytes = service.export_to_csv_bytes(results)

        # Should decode as UTF-8 without error
        decoded = csv_bytes.decode("utf-8")
        assert "Русский" in decoded

    def test_export_to_json_bytes_is_utf8_encoded(self) -> None:
        """Test that JSON bytes are UTF-8 encoded."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [
            create_sample_search_result(
                text_content="Русский текст",
            )
        ]

        json_bytes = service.export_to_json_bytes(results)

        # Should decode as UTF-8 without error
        decoded = json_bytes.decode("utf-8")
        assert "Русский" in decoded


class TestExportWithQuery:
    """Tests for including search query in export."""

    def test_export_to_json_can_include_query(self) -> None:
        """Test that JSON export can include the search query."""
        from src.tnse.export.service import ExportService

        service = ExportService()
        results = [create_sample_search_result()]

        json_output = service.export_to_json(results, query="corruption news")

        parsed = json.loads(json_output)
        assert parsed.get("query") == "corruption news"

    def test_export_to_csv_can_include_query_in_filename(self) -> None:
        """Test that CSV export can generate a filename from query."""
        from src.tnse.export.service import ExportService

        service = ExportService()

        filename = service.generate_filename("csv", query="corruption news")

        assert filename.endswith(".csv")
        assert "corruption" in filename.lower() or "export" in filename.lower()

    def test_generate_filename_for_json(self) -> None:
        """Test that JSON filename is generated correctly."""
        from src.tnse.export.service import ExportService

        service = ExportService()

        filename = service.generate_filename("json", query="test query")

        assert filename.endswith(".json")

    def test_generate_filename_sanitizes_query(self) -> None:
        """Test that filename generator sanitizes special characters."""
        from src.tnse.export.service import ExportService

        service = ExportService()

        filename = service.generate_filename("csv", query="test/query:with*special")

        # Should not contain special characters that could cause issues
        assert "/" not in filename
        assert ":" not in filename
        assert "*" not in filename
