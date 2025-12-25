"""
TNSE Engagement Module

Provides services for extracting and calculating engagement metrics.

Work Stream: WS-2.1 - Engagement Metrics

Requirements addressed:
- REQ-MO-002: System MUST retrieve and display view counts for each post
- REQ-MO-003: System MUST count EACH emoji reaction type separately
- REQ-MO-004: System MUST calculate a "reaction score" based on individual emoji counts
- REQ-MO-006: System MUST rank posts using: views, reaction score, and relative engagement
- REQ-MO-007: System SHOULD allow users to configure reaction score weights
- NFR-D-002: Engagement metrics MUST be stored with timestamps
"""

from src.tnse.engagement.service import EngagementService

__all__ = ["EngagementService"]
