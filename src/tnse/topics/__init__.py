"""
TNSE Topics Module

Provides topic management functionality for saving and retrieving
search configurations.

Work Stream: WS-3.1 - Saved Topics
"""

from src.tnse.topics.service import TopicService
from src.tnse.topics.templates import (
    BUILTIN_TEMPLATES,
    get_template_by_name,
    get_all_templates,
)

__all__ = [
    "TopicService",
    "BUILTIN_TEMPLATES",
    "get_template_by_name",
    "get_all_templates",
]
