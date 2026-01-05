# WS-5.7: Cost Tracking & Monitoring

## Summary

Implemented comprehensive LLM cost tracking and monitoring for the TNSE project.
This enables visibility into token usage, cost estimation, and budget management
for LLM API calls.

## Work Done

### 1. CostTracker Module (`src/tnse/llm/cost_tracker.py`)

Created a new module with:

- **GROQ_PRICING**: Pricing constants for 7 Groq models plus a default fallback
- **estimate_cost()**: Calculate cost from token counts with Decimal precision
- **CostTracker class**:
  - `log_usage()` - Persist usage records to llm_usage_logs table
  - `get_daily_stats()` - Aggregate daily usage statistics
  - `get_weekly_stats()` - Aggregate weekly usage statistics
  - `get_monthly_stats()` - Aggregate monthly usage statistics
  - `check_daily_limit()` - Check if approaching/exceeding cost limit

### 2. Data Classes

- **DailyStats**: date, total_tokens, total_cost_usd, posts_processed, call_count
- **WeeklyStats**: week_start/end, total_tokens, total_cost_usd, posts_processed
- **MonthlyStats**: year, month, total_tokens, total_cost_usd, posts_processed
- **CostStatus**: status (ok/warning/exceeded), current_cost, limit, percentage_used

### 3. Alert Thresholds

- Warning logged at 80% of daily limit
- Error logged when limit exceeded (100%)
- Configurable via `LLM_DAILY_COST_LIMIT_USD` environment variable

### 4. Bot Integration

Updated `/stats llm` command in `llm_handlers.py` to use CostTracker:
- Shows daily/weekly/monthly token usage and costs
- Displays cost limit status with warnings
- Shows total enriched posts count

### 5. Configuration

Added to `.env.example`:
```
LLM_DAILY_COST_LIMIT_USD=10.00
```

## Testing

### Unit Tests (35 tests)

All tests in `tests/unit/llm/test_cost_tracker.py`:

- TestGroqPricingConstants (5 tests)
- TestCostEstimation (5 tests)
- TestCostTracker (4 tests)
- TestUsageLogging (3 tests)
- TestDailyStats (3 tests)
- TestWeeklyStats (1 test)
- TestMonthlyStats (2 tests)
- TestCostAlerts (3 tests)
- TestStatsFormatting (3 tests)
- TestAverageTokensPerPost (2 tests)
- TestCostSettingsIntegration (2 tests)
- TestCostTrackerExports (2 tests)

### Test Results

```
35 passed in 87.28s
Full test suite: 1420 passed, 3 failed (pre-existing), 2 skipped
```

## Key Decisions

1. **Decimal Precision**: Used Python Decimal for cost calculations to avoid
   floating-point precision issues in financial calculations.

2. **Groq Pricing**: Pricing rates stored per 1M tokens as floats, with the
   estimate_cost function handling the conversion to per-token costs.

3. **Warning Threshold**: Set at 80% of daily limit to give users time to
   react before hitting the hard limit.

4. **Stats Formatting**: Created `format_llm_stats()` function for consistent
   display in Telegram messages.

## Files Changed

- `src/tnse/llm/cost_tracker.py` (new) - 400 lines
- `src/tnse/llm/__init__.py` (updated) - Added exports
- `src/tnse/bot/llm_handlers.py` (updated) - Integrated CostTracker
- `tests/unit/llm/test_cost_tracker.py` (new) - 35 tests
- `.env.example` (updated) - Added LLM_DAILY_COST_LIMIT_USD
- `docs/WS-5-TASK-BREAKDOWN.md` (updated) - Marked WS-5.7 complete
- `plans/roadmap.md` (updated) - Added WS-5.7 completion

## Next Steps

- WS-5.8: Documentation & Testing (final documentation and end-to-end tests)
- Optional: Prometheus/Grafana metrics integration for dashboards

## Session Information

- **Date:** 2026-01-05
- **Session ID:** tdd-coder-ws57
- **Duration:** ~2 hours
- **TDD Phases Completed:** RED, GREEN (35 tests passing)
