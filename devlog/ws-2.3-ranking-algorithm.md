# WS-2.3: Ranking Algorithm - Development Log

## Work Stream Information

| Field | Value |
|-------|-------|
| **Work Stream ID** | WS-2.3 |
| **Name** | Metrics-Based Ranking |
| **Started** | 2025-12-26 |
| **Completed** | 2025-12-26 |
| **Status** | Complete |

---

## Summary

Implemented a comprehensive RankingService for ranking posts by engagement and recency. The service provides configurable time windows, recency weighting, multiple sorting modes, and integrates seamlessly with the existing EngagementService data format.

---

## Implementation Details

### New Files Created

1. **`src/tnse/ranking/__init__.py`**
   - Module initialization with RankingService, RankedPost, and SortMode exports

2. **`src/tnse/ranking/service.py`**
   - Main RankingService class with all ranking logic
   - SortMode enum for sorting options
   - RankedPost dataclass for result representation

3. **`tests/unit/ranking/__init__.py`**
   - Test module initialization

4. **`tests/unit/ranking/test_ranking_service.py`**
   - 48 unit tests for RankingService

### Key Features Implemented

#### 1. SortMode Enumeration
Available sorting options:
| Mode | Description |
|------|-------------|
| COMBINED | Combined engagement * recency score |
| VIEWS | Sort by view count (highest first) |
| REACTIONS | Sort by reaction score (highest first) |
| ENGAGEMENT | Sort by relative engagement (highest first) |
| RECENCY | Sort by post time (newest first) |

#### 2. Recency Factor Calculation
Implements time-decay for post freshness:
```python
recency_factor = max(0, 1 - hours_since_post / time_window_hours)
```

Properties:
- Brand new post: recency_factor = 1.0
- Post at half of time window: recency_factor = 0.5
- Post at or beyond time window: recency_factor = 0.0
- Future posts capped at 1.0 (edge case)

#### 3. Combined Score Calculation
Implements configurable weighted combination:
```python
combined = engagement * (1 - recency_weight + recency_factor * recency_weight)
```

With different recency_weight values:
- **recency_weight=1.0**: `combined = engagement * recency_factor`
- **recency_weight=0.0**: `combined = engagement` (recency ignored)
- **recency_weight=0.5**: `combined = engagement * (0.5 + 0.5 * recency_factor)`

This formula allows smooth interpolation between pure engagement ranking and engagement-with-recency ranking.

#### 4. Configurable Parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| time_window_hours | 24 | Hours after which recency = 0 |
| recency_weight | 1.0 | Weight for recency in combined score |

#### 5. RankedPost Dataclass
Each ranked post includes:
- post_id (UUID)
- view_count (int)
- reaction_score (float)
- relative_engagement (float)
- posted_at (datetime)
- combined_score (float) - always computed

---

## Requirements Addressed

| Requirement ID | Description | Status |
|----------------|-------------|--------|
| REQ-MO-006 | System MUST rank posts using: views, reaction score, and relative engagement | Implemented |
| Combined Score | Ranking by combined score: engagement * recency | Implemented |
| Sorting Options | views, reactions, engagement, recency, combined | Implemented |
| Configurable Window | Configurable time window (default 24 hours) | Implemented |
| Configurable Weight | Configurable weight for recency vs engagement | Implemented |

---

## Test Coverage

### Unit Tests (48 tests)
- TestRankingServiceExists: 2 tests
- TestSortModeEnum: 6 tests
- TestRankedPostDataclass: 3 tests
- TestRankingConfiguration: 4 tests
- TestRecencyFactorCalculation: 6 tests
- TestCombinedScoreCalculation: 5 tests
- TestCalculateCombinedScoreForPost: 3 tests
- TestRankingPosts: 4 tests
- TestSortByViews: 1 test
- TestSortByReactions: 1 test
- TestSortByEngagement: 1 test
- TestSortByRecency: 1 test
- TestEdgeCases: 6 tests
- TestRankingWithMultiplePosts: 2 tests
- TestCombinedScoreAccessor: 2 tests
- TestRankingServiceIntegrationWithEngagementService: 1 test

**All 48 tests pass.**

**Full test suite: 475 tests pass (no regressions).**

---

## Decisions Made

### 1. Weighted Recency Formula
**Decision:** Use formula `(1 - recency_weight + recency_factor * recency_weight)` instead of simple multiplication.

**Rationale:**
- Allows smooth interpolation between pure engagement and engagement*recency
- recency_weight=0.5 gives 50% base + 50% weighted by recency
- More flexible for tuning ranking behavior
- Old posts with high engagement still get partial score when recency_weight < 1.0

### 2. Always Compute Combined Score
**Decision:** Always compute combined_score for RankedPost, even when sorting by other criteria.

**Rationale:**
- Consistent data structure
- Combined score useful for display even when sorted differently
- Minor performance impact (one calculation per post)

### 3. Handle Edge Cases Gracefully
**Decision:** Handle naive datetime, missing fields, and future timestamps without raising exceptions.

**Rationale:**
- Robust handling of real-world data inconsistencies
- Naive datetime treated as UTC
- Missing relative_engagement defaults to 0.0
- Missing posted_at defaults to current time
- Future posts capped at recency=1.0

### 4. Stable Sorting
**Decision:** Use Python's stable sort behavior for posts with equal values.

**Rationale:**
- Maintains input order for ties
- Predictable, deterministic results
- No additional complexity needed

---

## Integration Notes

The RankingService integrates with:

1. **EngagementService** (`src/tnse/engagement/service.py`)
   - Accepts data format from `create_engagement_metrics()`
   - Uses relative_engagement field for ranking

2. **SearchService** (`src/tnse/search/service.py`)
   - Can be used to rank search results
   - Will be integrated in WS-2.4

---

## Usage Example

```python
from src.tnse.ranking.service import RankingService, SortMode
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Create service with custom configuration
service = RankingService(
    time_window_hours=24,  # 24-hour recency window
    recency_weight=0.8,     # 80% weight on recency
)

# Prepare posts with engagement data
now = datetime.now(timezone.utc)
posts = [
    {
        "post_id": uuid4(),
        "view_count": 12500,
        "reaction_score": 379.0,
        "relative_engagement": 0.25,
        "posted_at": now - timedelta(hours=2),
    },
    {
        "post_id": uuid4(),
        "view_count": 5000,
        "reaction_score": 150.0,
        "relative_engagement": 0.1,
        "posted_at": now - timedelta(hours=12),
    },
]

# Rank by combined score
ranked = service.rank_posts(posts, sort_mode=SortMode.COMBINED)
for post in ranked:
    print(f"Score: {post.combined_score:.3f}, Views: {post.view_count}")

# Rank by different criteria
by_views = service.rank_posts(posts, sort_mode=SortMode.VIEWS)
by_recency = service.rank_posts(posts, sort_mode=SortMode.RECENCY)
```

---

## Next Steps

This work stream enables:
- WS-2.4: Search Bot Commands (can now rank search results)
- WS-2.5: Export Functionality (export ranked results)

---

*End of Development Log*
