"""
Unit tests for topic templates.

Tests cover:
- Built-in template definitions
- Template retrieval by name
- Listing all templates

Work Stream: WS-3.1 - Saved Topics
"""

import pytest

from src.tnse.topics.templates import (
    BUILTIN_TEMPLATES,
    TopicTemplateData,
    get_template_by_name,
    get_all_templates,
)


class TestTopicTemplateData:
    """Tests for the TopicTemplateData dataclass."""

    def test_create_template_data(self) -> None:
        """TopicTemplateData can be created with all fields."""
        template = TopicTemplateData(
            name="corruption",
            keywords="corruption, bribery, scandal, investigation, fraud",
            description="News about corruption and bribery scandals",
            category="politics",
        )

        assert template.name == "corruption"
        assert "corruption" in template.keywords
        assert "bribery" in template.keywords
        assert template.description is not None
        assert template.category == "politics"

    def test_template_data_to_dict(self) -> None:
        """TopicTemplateData can be converted to dictionary."""
        template = TopicTemplateData(
            name="tech",
            keywords="technology, AI",
            description="Tech news",
            category="technology",
        )

        template_dict = template.to_dict()

        assert template_dict["name"] == "tech"
        assert template_dict["keywords"] == "technology, AI"
        assert template_dict["description"] == "Tech news"
        assert template_dict["category"] == "technology"


class TestBuiltinTemplates:
    """Tests for built-in template constants."""

    def test_builtin_templates_contains_corruption(self) -> None:
        """BUILTIN_TEMPLATES contains corruption template."""
        names = [template.name for template in BUILTIN_TEMPLATES]
        assert "corruption" in names

    def test_builtin_templates_contains_politics(self) -> None:
        """BUILTIN_TEMPLATES contains politics template."""
        names = [template.name for template in BUILTIN_TEMPLATES]
        assert "politics" in names

    def test_builtin_templates_contains_tech(self) -> None:
        """BUILTIN_TEMPLATES contains tech template."""
        names = [template.name for template in BUILTIN_TEMPLATES]
        assert "tech" in names

    def test_builtin_templates_contains_science(self) -> None:
        """BUILTIN_TEMPLATES contains science template."""
        names = [template.name for template in BUILTIN_TEMPLATES]
        assert "science" in names

    def test_builtin_templates_contains_business(self) -> None:
        """BUILTIN_TEMPLATES contains business template."""
        names = [template.name for template in BUILTIN_TEMPLATES]
        assert "business" in names

    def test_corruption_template_has_required_keywords(self) -> None:
        """Corruption template has required keywords."""
        template = get_template_by_name("corruption")
        assert template is not None

        keywords_lower = template.keywords.lower()
        assert "corruption" in keywords_lower
        assert "bribery" in keywords_lower
        assert "scandal" in keywords_lower
        assert "investigation" in keywords_lower
        assert "fraud" in keywords_lower

    def test_politics_template_has_required_keywords(self) -> None:
        """Politics template has required keywords."""
        template = get_template_by_name("politics")
        assert template is not None

        keywords_lower = template.keywords.lower()
        assert "government" in keywords_lower
        assert "election" in keywords_lower
        assert "parliament" in keywords_lower
        assert "minister" in keywords_lower
        assert "president" in keywords_lower

    def test_tech_template_has_required_keywords(self) -> None:
        """Tech template has required keywords."""
        template = get_template_by_name("tech")
        assert template is not None

        keywords_lower = template.keywords.lower()
        assert "technology" in keywords_lower
        assert "ai" in keywords_lower
        assert "startup" in keywords_lower
        assert "innovation" in keywords_lower
        assert "software" in keywords_lower

    def test_science_template_has_required_keywords(self) -> None:
        """Science template has required keywords."""
        template = get_template_by_name("science")
        assert template is not None

        keywords_lower = template.keywords.lower()
        assert "science" in keywords_lower
        assert "research" in keywords_lower
        assert "discovery" in keywords_lower
        assert "study" in keywords_lower
        assert "experiment" in keywords_lower

    def test_business_template_has_required_keywords(self) -> None:
        """Business template has required keywords."""
        template = get_template_by_name("business")
        assert template is not None

        keywords_lower = template.keywords.lower()
        assert "business" in keywords_lower
        assert "economy" in keywords_lower
        assert "market" in keywords_lower
        assert "finance" in keywords_lower
        assert "investment" in keywords_lower


class TestGetTemplateByName:
    """Tests for get_template_by_name function."""

    def test_get_template_by_name_returns_template(self) -> None:
        """get_template_by_name returns template if it exists."""
        template = get_template_by_name("corruption")

        assert template is not None
        assert template.name == "corruption"

    def test_get_template_by_name_returns_none_for_nonexistent(self) -> None:
        """get_template_by_name returns None for nonexistent template."""
        template = get_template_by_name("nonexistent_template")

        assert template is None

    def test_get_template_by_name_is_case_insensitive(self) -> None:
        """get_template_by_name is case insensitive."""
        template1 = get_template_by_name("Corruption")
        template2 = get_template_by_name("CORRUPTION")
        template3 = get_template_by_name("corruption")

        assert template1 is not None
        assert template2 is not None
        assert template3 is not None
        assert template1.name == template2.name == template3.name


class TestGetAllTemplates:
    """Tests for get_all_templates function."""

    def test_get_all_templates_returns_list(self) -> None:
        """get_all_templates returns a list of templates."""
        templates = get_all_templates()

        assert isinstance(templates, list)
        assert len(templates) >= 5  # At least 5 required templates

    def test_get_all_templates_returns_template_data_objects(self) -> None:
        """get_all_templates returns TopicTemplateData objects."""
        templates = get_all_templates()

        for template in templates:
            assert isinstance(template, TopicTemplateData)

    def test_get_all_templates_contains_all_required_templates(self) -> None:
        """get_all_templates contains all required built-in templates."""
        templates = get_all_templates()
        names = [template.name for template in templates]

        required_names = ["corruption", "politics", "tech", "science", "business"]
        for name in required_names:
            assert name in names, f"Missing required template: {name}"
