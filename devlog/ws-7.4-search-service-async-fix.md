# WS-7.4: SearchService Async/Sync Context Manager Bug Fix

## Date
2026-01-04

## Status
Complete

## Summary
Fixed a bug in `SearchService._execute_search()` where synchronous context manager was used with an async session factory, causing `TypeError: 'AsyncSession' object does not support the context manager protocol`.

## Problem Description

The search service was using a synchronous context manager (`with`) with SQLAlchemy's `async_sessionmaker`, which returns `AsyncSession` objects. `AsyncSession` only implements async context manager protocol (`__aenter__`/`__aexit__`), not sync (`__enter__`/`__exit__`).

### Error Message
```
TypeError: 'AsyncSession' object does not support the context manager protocol
```

### Root Cause (src/tnse/search/service.py line 244)
```python
# WRONG - sync context manager with async session
with self.session_factory() as session:
    result = session.execute(...)  # Also missing await

# CORRECT - async context manager
async with self.session_factory() as session:
    result = await session.execute(...)
```

## Solution

### Code Changes

1. **src/tnse/search/service.py** - Fixed line 244:
   - Changed `with self.session_factory()` to `async with self.session_factory()`
   - Changed `session.execute()` to `await session.execute()`

2. **tests/unit/search/test_search_service.py** - Updated test mocks:
   - Added `AsyncSessionMock` class that implements async context manager protocol
   - Updated all tests using sync mocks to use the new async-compatible mock

3. **tests/unit/search/test_search_service_async.py** - New test file:
   - Added 5 tests specifically for async context manager behavior
   - Tests use `MockAsyncSession` that only implements async protocol
   - Tests fail if code uses sync `with` instead of `async with`

## TDD Process

### RED Phase
- Wrote failing tests in `test_search_service_async.py`
- Tests used `MockAsyncSession` that deliberately lacks `__enter__`/`__exit__`
- All 5 tests failed with `TypeError: 'MockAsyncSession' object does not support the context manager protocol`

### GREEN Phase
- Changed `with` to `async with` in service.py
- Changed `session.execute()` to `await session.execute()`
- All 5 new tests passed

### REFACTOR Phase
- Updated existing tests in `test_search_service.py` to use `AsyncSessionMock`
- Ensured all 42 search-related tests pass

## Testing

### Test Results
- 5 new async context manager tests: PASSED
- 42 total search tests: PASSED
- 956 total unit tests: PASSED (12 pre-existing failures unrelated to this fix)

### Pre-existing Failures (Not Related to This Fix)
- 2 performance tests (machine-dependent flakiness)
- 8 topic handler tests (WS-7.5 work stream)
- 2 config tests (test environment issues)

## Files Changed

| File | Changes |
|------|---------|
| `src/tnse/search/service.py` | Fixed async context manager and await |
| `tests/unit/search/test_search_service.py` | Added AsyncSessionMock, updated test mocks |
| `tests/unit/search/test_search_service_async.py` | New file with 5 async tests |
| `plans/roadmap.md` | Added WS-7.4, marked complete |

## Lessons Learned

1. **SQLAlchemy Async Sessions**: When using `async_sessionmaker`, always use `async with` for context management and `await` for database operations.

2. **Test Mock Design**: Mock objects for async sessions should only implement async protocol (`__aenter__`/`__aexit__`) to catch sync/async mismatches early.

3. **TDD Value**: Writing tests that demonstrate the bug before fixing ensures the fix is correct and prevents regression.

## Related Work Streams
- WS-7.3: Search Service Injection Bug (completed prior)
- WS-7.5: TopicService Injection Bug (pending)
