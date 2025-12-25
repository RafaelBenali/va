"""
TNSE Export Service

Provides functionality to export search results to CSV and JSON formats.

Work Stream: WS-2.5 - Export Functionality

Requirements addressed:
- REQ-RP-005: System MUST support export to CSV, JSON, and formatted text
- REQ-RP-001: System MUST display ranked news list with direct Telegram links
- REQ-RP-002: System SHALL show engagement metrics for each item
"""

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from src.tnse.search.service import SearchResult


@dataclass
class ExportService:
    """Service for exporting search results to various formats.

    Provides methods to export search results to CSV and JSON formats,
    with support for Cyrillic text, Telegram links, and proper encoding.

    Example:
        >>> service = ExportService()
        >>> csv_output = service.export_to_csv(search_results)
        >>> json_output = service.export_to_json(search_results)
    """

    def export_to_csv(self, results: list[SearchResult]) -> str:
        """Export search results to CSV format.

        Generates a CSV string with all search result data including
        Telegram links and engagement metrics.

        Args:
            results: List of SearchResult objects to export.

        Returns:
            CSV formatted string with header row and data rows.
        """
        output = io.StringIO()

        fieldnames = [
            "channel_username",
            "channel_title",
            "text_preview",
            "view_count",
            "reaction_score",
            "relative_engagement",
            "published_at",
            "telegram_link",
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            writer.writerow({
                "channel_username": result.channel_username,
                "channel_title": result.channel_title,
                "text_preview": result.preview,
                "view_count": result.view_count,
                "reaction_score": result.reaction_score,
                "relative_engagement": result.relative_engagement,
                "published_at": result.published_at.isoformat(),
                "telegram_link": result.telegram_link,
            })

        return output.getvalue()

    def export_to_csv_bytes(self, results: list[SearchResult]) -> bytes:
        """Export search results to CSV format as bytes.

        Generates a UTF-8 encoded bytes object suitable for file transmission.

        Args:
            results: List of SearchResult objects to export.

        Returns:
            UTF-8 encoded bytes of the CSV content.
        """
        csv_string = self.export_to_csv(results)
        return csv_string.encode("utf-8")

    def export_to_json(
        self,
        results: list[SearchResult],
        query: Optional[str] = None,
    ) -> str:
        """Export search results to JSON format.

        Generates a JSON string with all search result data including
        metadata about the export.

        Args:
            results: List of SearchResult objects to export.
            query: Optional search query to include in the export metadata.

        Returns:
            JSON formatted string with results and metadata.
        """
        export_data = {
            "total": len(results),
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "results": [],
        }

        if query is not None:
            export_data["query"] = query

        for result in results:
            export_data["results"].append({
                "post_id": result.post_id,
                "channel_id": result.channel_id,
                "channel_username": result.channel_username,
                "channel_title": result.channel_title,
                "text_content": result.text_content,
                "text_preview": result.preview,
                "view_count": result.view_count,
                "reaction_score": result.reaction_score,
                "relative_engagement": result.relative_engagement,
                "published_at": result.published_at.isoformat(),
                "telegram_message_id": result.telegram_message_id,
                "telegram_link": result.telegram_link,
            })

        return json.dumps(export_data, ensure_ascii=False, indent=2)

    def export_to_json_bytes(self, results: list[SearchResult]) -> bytes:
        """Export search results to JSON format as bytes.

        Generates a UTF-8 encoded bytes object suitable for file transmission.

        Args:
            results: List of SearchResult objects to export.

        Returns:
            UTF-8 encoded bytes of the JSON content.
        """
        json_string = self.export_to_json(results)
        return json_string.encode("utf-8")

    def generate_filename(
        self,
        format_type: str,
        query: Optional[str] = None,
    ) -> str:
        """Generate a filename for the export file.

        Creates a sanitized filename based on the format type and optional
        search query.

        Args:
            format_type: The file format (e.g., "csv", "json").
            query: Optional search query to include in the filename.

        Returns:
            A sanitized filename string with the appropriate extension.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if query:
            # Sanitize the query for use in filename
            sanitized_query = self._sanitize_for_filename(query)
            # Limit length to avoid overly long filenames
            sanitized_query = sanitized_query[:30]
            filename = f"tnse_export_{sanitized_query}_{timestamp}.{format_type}"
        else:
            filename = f"tnse_export_{timestamp}.{format_type}"

        return filename

    def _sanitize_for_filename(self, text: str) -> str:
        """Sanitize text for use in a filename.

        Removes or replaces characters that are not safe for filenames.

        Args:
            text: The text to sanitize.

        Returns:
            A sanitized string safe for use in filenames.
        """
        # Replace spaces with underscores
        sanitized = text.replace(" ", "_")
        # Remove characters that are problematic in filenames
        sanitized = re.sub(r'[<>:"/\\|?*]', "", sanitized)
        # Remove any remaining non-alphanumeric characters except underscores and hyphens
        sanitized = re.sub(r'[^\w\-]', "", sanitized, flags=re.UNICODE)
        # Convert to lowercase for consistency
        sanitized = sanitized.lower()

        return sanitized
