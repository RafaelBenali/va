# WS-5.1: Groq Client Integration

## Summary

Implemented the Groq LLM client integration as the first step in the RAG Without Vectors feature. This provides the foundation for LLM-powered post enrichment including keyword extraction, categorization, and sentiment analysis.

## Date

2026-01-05

## Status

Complete

## Objectives

1. Set up Groq Python SDK for LLM API calls
2. Create configuration settings for Groq parameters
3. Implement async client with rate limiting
4. Support JSON mode for structured outputs
5. Handle errors gracefully with retries
6. Establish LLMProvider abstraction for future providers

## Implementation Details

### Configuration (GroqSettings)

Added `GroqSettings` class to `src/tnse/core/config.py` with the following parameters:

| Setting | Default | Description |
|---------|---------|-------------|
| `GROQ_API_KEY` | None | API key (required) |
| `GROQ_MODEL` | qwen-qwq-32b | Model ID |
| `GROQ_MAX_TOKENS` | 1024 | Max response tokens |
| `GROQ_TEMPERATURE` | 0.1 | Generation temperature |
| `GROQ_ENABLED` | false | Enable LLM features |
| `GROQ_RATE_LIMIT_RPM` | 30 | Requests per minute |
| `GROQ_TIMEOUT_SECONDS` | 30.0 | Request timeout |
| `GROQ_MAX_RETRIES` | 3 | Retry attempts |

### LLM Provider Abstraction

Created `src/tnse/llm/base.py` with:

- **CompletionResult**: Dataclass containing:
  - `content`: Generated text
  - `prompt_tokens`, `completion_tokens`, `total_tokens`: Token usage
  - `model`: Model used
  - `duration_ms`: Request duration
  - `created_at`: Timestamp
  - `parsed_json`: Parsed JSON for JSON mode

- **LLMProvider**: Abstract base class defining the interface:
  - `complete()`: Generate text completion
  - `complete_json()`: Generate JSON completion
  - `is_available()`: Check if provider is configured

### Groq Client Implementation

Created `src/tnse/llm/groq_client.py` with:

- **GroqClient**: Implements LLMProvider with:
  - Async context manager support (`async with`)
  - Rate limiting via RateLimiter class
  - JSON mode via `response_format={"type": "json_object"}`
  - Automatic retry with exponential backoff
  - Proper error handling for common failure modes

- **RateLimiter**: Token bucket rate limiter:
  - Configurable requests per minute
  - Sliding window approach
  - Async-safe with lock protection

- **Custom Exceptions**:
  - `GroqConfigurationError`: Missing API key
  - `GroqAuthenticationError`: Invalid API key
  - `GroqRateLimitError`: Rate limit exceeded after retries
  - `GroqTimeoutError`: Request timeout
  - `JSONParseError`: Invalid JSON response

### Usage Example

```python
from src.tnse.llm import GroqClient

async with GroqClient(api_key="your-key") as client:
    # Text completion
    result = await client.complete("Summarize this text...")
    print(result.content)
    print(f"Tokens used: {result.total_tokens}")

    # JSON completion
    result = await client.complete_json(
        prompt="Extract keywords as JSON",
        system_message="Return JSON with 'keywords' array"
    )
    keywords = result.parsed_json["keywords"]
```

### Test Coverage

Added 30 comprehensive unit tests in `tests/unit/llm/test_groq_client.py`:

| Test Class | Tests | Description |
|------------|-------|-------------|
| TestGroqSettings | 3 | Configuration loading |
| TestGroqClientCreation | 5 | Client initialization |
| TestGroqClientAsyncContext | 2 | Context manager |
| TestGroqClientCompletion | 2 | Text completions |
| TestGroqClientJSONMode | 3 | JSON mode |
| TestGroqClientRateLimiting | 3 | Rate limiting |
| TestGroqClientErrorHandling | 4 | Error scenarios |
| TestGroqClientResponseTracking | 2 | Response metadata |
| TestLLMProviderAbstraction | 3 | Base interface |
| TestGroqClientHealthCheck | 3 | Health checks |

All tests use mocked API responses and verify:
- Correct API call parameters
- Proper error handling
- Rate limiting behavior
- JSON parsing

## Files Changed

| File | Change |
|------|--------|
| `src/tnse/llm/__init__.py` | New - Package exports |
| `src/tnse/llm/base.py` | New - LLMProvider interface |
| `src/tnse/llm/groq_client.py` | New - GroqClient implementation |
| `src/tnse/core/config.py` | Updated - Added GroqSettings |
| `tests/unit/llm/test_groq_client.py` | New - 30 unit tests |
| `requirements.txt` | Updated - Added groq>=0.13.0 |
| `.env.example` | Updated - Added Groq config section |

## Decisions and Rationale

### Why Groq?

1. **Free Tier**: 30 RPM suitable for development and small deployments
2. **Fast Inference**: Groq's LPU provides low latency
3. **Model Selection**: Qwen-QWQ-32B is strong for reasoning and multilingual content
4. **JSON Mode**: Native support for structured outputs

### Why Abstract LLMProvider?

The `LLMProvider` abstraction allows easy switching to other providers (OpenAI, Anthropic) in the future without changing consuming code. The Settings already include placeholders for these providers.

### Rate Limiting Strategy

Implemented client-side rate limiting rather than relying on API errors because:
1. Prevents wasted API calls
2. Predictable request timing
3. Better user experience (no retry delays)

## Test Results

```
30 passed in 61.63s
Coverage: 97% for groq_client.py
Coverage: 92% for base.py
```

## Next Steps

WS-5.2: Database Schema (Post Enrichment)
- Create `post_enrichments` table
- Create `llm_usage_logs` table
- Add GIN indexes for keyword arrays

## Dependencies

- `groq>=0.13.0` added to requirements.txt
- Python 3.12+ (uses `X | None` syntax)
