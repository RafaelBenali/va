"""
TNSE Topic Templates Module

Provides pre-built topic templates for common search configurations.
Templates are immutable definitions that users can use immediately.

Work Stream: WS-3.1 - Saved Topics

Pre-built Templates:
1. "corruption" - corruption, bribery, scandal, investigation, fraud
2. "politics" - government, election, parliament, minister, president
3. "tech" - technology, AI, startup, innovation, software
4. "science" - science, research, discovery, study, experiment
5. "business" - business, economy, market, finance, investment
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class TopicTemplateData:
    """Immutable data structure for topic templates.

    Represents a pre-built template that users can use for quick searches.

    Attributes:
        name: Unique template identifier.
        keywords: Comma-separated search keywords.
        description: Human-readable description of the template.
        category: Template category for grouping (optional).
    """

    name: str
    keywords: str
    description: str = ""
    category: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert template to dictionary representation.

        Returns:
            Dictionary with template fields.
        """
        return {
            "name": self.name,
            "keywords": self.keywords,
            "description": self.description,
            "category": self.category,
        }


# Pre-built templates as specified in requirements
BUILTIN_TEMPLATES: list[TopicTemplateData] = [
    TopicTemplateData(
        name="corruption",
        keywords="corruption, bribery, scandal, investigation, fraud",
        description="News about corruption, bribery scandals, and fraud investigations",
        category="politics",
    ),
    TopicTemplateData(
        name="politics",
        keywords="government, election, parliament, minister, president",
        description="Political news including elections, government, and officials",
        category="politics",
    ),
    TopicTemplateData(
        name="tech",
        keywords="technology, AI, startup, innovation, software",
        description="Technology news including AI, startups, and software",
        category="technology",
    ),
    TopicTemplateData(
        name="science",
        keywords="science, research, discovery, study, experiment",
        description="Scientific news including research and discoveries",
        category="science",
    ),
    TopicTemplateData(
        name="business",
        keywords="business, economy, market, finance, investment",
        description="Business and economic news including markets and investments",
        category="business",
    ),
]

# Create a lookup dictionary for fast template retrieval
_TEMPLATE_LOOKUP: dict[str, TopicTemplateData] = {
    template.name.lower(): template for template in BUILTIN_TEMPLATES
}


def get_template_by_name(name: str) -> Optional[TopicTemplateData]:
    """Retrieve a template by its name.

    Args:
        name: The template name (case-insensitive).

    Returns:
        TopicTemplateData if found, None otherwise.
    """
    return _TEMPLATE_LOOKUP.get(name.lower())


def get_all_templates() -> list[TopicTemplateData]:
    """Get all available templates.

    Returns:
        List of all TopicTemplateData objects.
    """
    return list(BUILTIN_TEMPLATES)
