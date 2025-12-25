# WS-1.2: Database Schema - Development Log

## Work Stream Information

| Field | Value |
|-------|-------|
| **Work Stream ID** | WS-1.2 |
| **Name** | Database Schema (Simplified) |
| **Started** | 2025-12-25 |
| **Completed** | 2025-12-25 |
| **Developer** | Claude Opus 4.5 |

---

## Summary

Implemented the complete database schema for the TNSE (Telegram News Search Engine) using SQLAlchemy ORM with PostgreSQL-specific features. The schema covers all core entities: channels, posts, engagement metrics, saved topics, and bot settings.

---

## Implementation Details

### Models Created

1. **Channel Models**
   - `Channel`: Stores monitored Telegram channel metadata (telegram_id, username, title, description, subscriber_count, etc.)
   - `ChannelHealthLog`: Tracks channel health check history with status and error messages
   - `ChannelStatus` enum: HEALTHY, RATE_LIMITED, INACCESSIBLE, REMOVED

2. **Post Models**
   - `Post`: Core post entity linking to channels with forwarding detection
   - `PostContent`: Separate table for text content with language detection support
   - `PostMedia`: One-to-many relationship for media attachments (photo, video, document, audio, animation)
   - `MediaType` enum: PHOTO, VIDEO, DOCUMENT, AUDIO, ANIMATION

3. **Engagement Models**
   - `EngagementMetrics`: Time-series engagement data (views, forwards, replies, reaction_score, relative_engagement)
   - `ReactionCount`: Per-emoji reaction counts with unique constraint on (engagement_metrics_id, emoji)

4. **Topic Models**
   - `SavedTopic`: User-saved search configurations with keywords and search_config JSON
   - `TopicTemplate`: Pre-built topic templates with category grouping
   - `BotSettings`: Simple key-value store for bot configuration

### Design Decisions

1. **UUID Primary Keys**: All tables use UUID primary keys via PostgreSQL's `uuid-ossp` extension for distributed compatibility.

2. **Separate Content Table**: `PostContent` is separated from `Post` to optimize queries that don't need full text content and to support future full-text search indexing.

3. **One-to-Many Media**: `PostMedia` allows multiple media items per post (photo albums, etc.) rather than a single media field.

4. **Time-Series Engagement**: `EngagementMetrics` stores snapshots with `collected_at` timestamps to track engagement over time, not just current state.

5. **Per-Emoji Reactions**: `ReactionCount` stores individual emoji counts separately rather than a JSON blob, enabling efficient querying and aggregation by reaction type.

6. **Configurable Reaction Weights**: The `reaction_score` is computed at collection time using configurable weights from settings, not stored as raw counts.

7. **Soft Delete Pattern**: Channels have `is_active` flag rather than hard deletion to preserve historical data.

### Indexes Created

- `ix_channels_telegram_id`: Fast lookup by Telegram's channel ID
- `ix_channels_username`: Fast lookup by @username
- `ix_posts_channel_id`: Posts by channel
- `ix_posts_telegram_message_id`: Deduplication of messages
- `ix_posts_published_at`: Time-range queries for 24-hour window
- `ix_engagement_metrics_collected_at`: Time-series analysis
- `ix_engagement_metrics_post_id`: Metrics by post
- `ix_reaction_counts_emoji`: Filtering by reaction type
- `ix_saved_topics_name`: Topic lookup
- `ix_topic_templates_category`: Template grouping
- `ix_bot_settings_key`: Setting lookup

### Unique Constraints

- `channels.telegram_id`: Prevent duplicate channels
- `channels.username`: Prevent duplicate @usernames
- `uq_posts_channel_message`: (channel_id, telegram_message_id) - Prevent duplicate messages
- `uq_reaction_counts_metrics_emoji`: (engagement_metrics_id, emoji) - One count per emoji per metrics snapshot
- `saved_topics.name`: Unique topic names
- `topic_templates.name`: Unique template names
- `bot_settings.key`: Unique setting keys

### Files Created/Modified

- `src/tnse/db/__init__.py`: Module exports
- `src/tnse/db/base.py`: SQLAlchemy Base and mixins (TimestampMixin, UUIDPrimaryKeyMixin)
- `src/tnse/db/models.py`: All model definitions (635 lines)
- `alembic/env.py`: Alembic environment configuration
- `alembic/versions/9bab40e1a6eb_initial_schema_channels_posts_.py`: Initial migration

### Test Coverage

89 unit tests covering all models:

- `test_models_channel.py`: 22 tests for Channel, ChannelHealthLog, ChannelStatus
- `test_models_post.py`: 26 tests for Post, PostContent, PostMedia, MediaType
- `test_models_engagement.py`: 20 tests for EngagementMetrics, ReactionCount
- `test_models_topics.py`: 21 tests for SavedTopic, TopicTemplate, BotSettings

All tests follow TDD methodology - tests were written before implementation.

---

## Challenges and Solutions

### Challenge 1: Alembic Autogenerate Without Database

Alembic's autogenerate feature requires a database connection. Since no PostgreSQL was running locally, we created a manual migration script with explicit table definitions.

**Solution**: Created a comprehensive manual migration that mirrors the SQLAlchemy model definitions, including all indexes and constraints.

### Challenge 2: Pre-existing Config Test Failures

The existing `test_config.py` had 4 failing tests due to pydantic-settings configuration issues.

**Solution**: Fixed the config module to use `populate_by_name=True`, `validate_default=True`, and `validation_alias` instead of `alias` for fields that need both direct and environment variable access.

### Challenge 3: SQLAlchemy Column Index Checking

Tests checking for column indexes had syntax issues with SQLAlchemy's column collection.

**Solution**: Updated tests to check index by column name string rather than column object comparison.

---

## Requirements Addressed

| Requirement | Status |
|-------------|--------|
| REQ-CC-003: Channel metadata | Implemented in Channel model |
| REQ-CC-006: Channel health status | Implemented in ChannelHealthLog + ChannelStatus |
| REQ-NP-002: Extract text, images, video | Implemented in PostContent + PostMedia |
| REQ-NP-010: Detect forwarded content | Implemented in Post (is_forwarded, forward_from_*) |
| REQ-MO-002: View counts | Implemented in EngagementMetrics |
| REQ-MO-003: Per-emoji reaction counts | Implemented in ReactionCount |
| REQ-MO-004: Reaction score calculation | Implemented in EngagementMetrics.reaction_score |
| REQ-TC-003: Save topic configurations | Implemented in SavedTopic |
| REQ-TC-007: Topic templates | Implemented in TopicTemplate |
| NFR-D-002: Engagement timestamps | Implemented in EngagementMetrics.collected_at |

---

## Next Steps

With WS-1.2 complete, the following work streams can now proceed:

1. **WS-1.3: Telegram Bot Foundation** - Can use BotSettings for configuration
2. **WS-1.4: Telegram API Integration** - Will populate Channel and Post tables
3. **WS-1.6: Content Collection Pipeline** - Will create EngagementMetrics records

---

## Commits

1. `test: add failing tests for Channel and ChannelHealthLog models`
2. `feat: implement Channel and ChannelHealthLog database models`
3. `test: add failing tests for Post, PostContent, and PostMedia models`
4. `feat: implement Post, PostContent, and PostMedia database models`
5. `test: add failing tests for EngagementMetrics and ReactionCount models`
6. `feat: implement EngagementMetrics and ReactionCount database models`
7. `test: add failing tests for SavedTopic, TopicTemplate, and BotSettings models`
8. `feat: implement SavedTopic, TopicTemplate, and BotSettings database models`
9. `feat: add Alembic migrations for initial database schema`
10. `docs: update roadmap and devlog for WS-1.2`

---

*End of Development Log*
