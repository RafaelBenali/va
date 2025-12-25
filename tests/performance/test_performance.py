"""
TNSE Performance Benchmarks

Performance tests to ensure the application meets performance requirements:
- Search response time < 3 seconds (NFR-P-007)
- Ranking algorithm performance
- Database query performance
- Results formatting performance

Work Stream: WS-3.3 - Polish and Testing
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from src.tnse.ranking.service import RankingService, SortMode
from src.tnse.search.tokenizer import Tokenizer
from src.tnse.search.service import SearchResult
from src.tnse.bot.search_handlers import SearchFormatter


# Performance thresholds (in seconds)
# These are calibrated for reasonable test performance while ensuring
# the overall search response stays under the 3-second requirement
SEARCH_RESPONSE_THRESHOLD = 3.0  # NFR-P-007: < 3 seconds
RANKING_THRESHOLD = 1.0  # Ranking should complete in < 1 second
TOKENIZER_THRESHOLD = 0.1  # Tokenization should complete in < 100ms
FORMATTER_THRESHOLD = 0.5  # Formatting should complete in < 500ms
RECENCY_CALCULATION_THRESHOLD = 1.0  # Recency calculation for batch ops


@dataclass
class BenchmarkResult:
    """Result from a benchmark run."""

    name: str
    duration_seconds: float
    iterations: int
    threshold_seconds: float
    passed: bool
    details: Optional[str] = None

    @property
    def average_per_iteration(self) -> float:
        """Calculate average time per iteration."""
        return self.duration_seconds / self.iterations if self.iterations > 0 else 0

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"[{status}] {self.name}: {self.duration_seconds:.4f}s "
            f"({self.iterations} iterations, {self.average_per_iteration:.6f}s avg) "
            f"[threshold: {self.threshold_seconds}s]"
        )


def benchmark(
    func: Callable,
    iterations: int = 1,
    threshold: float = 1.0,
    name: Optional[str] = None,
    **kwargs: Any,
) -> BenchmarkResult:
    """
    Run a function multiple times and measure performance.

    Args:
        func: The function to benchmark.
        iterations: Number of times to run the function.
        threshold: Maximum acceptable duration in seconds.
        name: Name for the benchmark (defaults to function name).
        **kwargs: Arguments to pass to the function.

    Returns:
        BenchmarkResult with timing information.
    """
    benchmark_name = name or func.__name__

    start_time = time.perf_counter()
    for _ in range(iterations):
        func(**kwargs)
    end_time = time.perf_counter()

    duration = end_time - start_time
    passed = duration <= threshold

    return BenchmarkResult(
        name=benchmark_name,
        duration_seconds=duration,
        iterations=iterations,
        threshold_seconds=threshold,
        passed=passed,
    )


def create_sample_posts(count: int) -> list[dict[str, Any]]:
    """Create sample post data for testing."""
    reference_time = datetime.now(timezone.utc)

    posts = []
    for index in range(count):
        hours_ago = index % 24  # Distribute across 24 hours
        posts.append({
            "post_id": uuid4(),
            "view_count": 1000 + (index * 100),
            "reaction_score": 10.0 + (index * 2),
            "relative_engagement": 0.01 + (index * 0.005),
            "posted_at": reference_time - timedelta(hours=hours_ago),
        })

    return posts


def create_sample_search_results(count: int) -> list[SearchResult]:
    """Create sample SearchResult objects for testing."""
    reference_time = datetime.now(timezone.utc)

    results = []
    for index in range(count):
        hours_ago = index % 24
        results.append(
            SearchResult(
                post_id=str(uuid4()),
                channel_id=str(uuid4()),
                channel_username=f"channel_{index}",
                channel_title=f"Test Channel {index}",
                text_content=f"This is test post number {index}. " * 10,
                published_at=reference_time - timedelta(hours=hours_ago),
                view_count=1000 + (index * 100),
                reaction_score=10.0 + (index * 2),
                relative_engagement=0.01 + (index * 0.005),
                telegram_message_id=10000 + index,
            )
        )

    return results


class TestTokenizerPerformance:
    """Performance tests for the tokenizer."""

    def test_tokenizer_single_word_performance(self) -> None:
        """Test tokenization of single word queries."""
        tokenizer = Tokenizer()

        def tokenize_single():
            tokenizer.tokenize("corruption")

        result = benchmark(
            tokenize_single,
            iterations=1000,
            threshold=TOKENIZER_THRESHOLD,
            name="Tokenizer - Single Word (1000x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Tokenizer too slow: {result.duration_seconds}s > {result.threshold_seconds}s"

    def test_tokenizer_multi_word_performance(self) -> None:
        """Test tokenization of multi-word queries."""
        tokenizer = Tokenizer()

        def tokenize_multi():
            tokenizer.tokenize("corruption bribery political scandal investigation")

        result = benchmark(
            tokenize_multi,
            iterations=1000,
            threshold=TOKENIZER_THRESHOLD,
            name="Tokenizer - Multi Word (1000x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Tokenizer too slow: {result.duration_seconds}s > {result.threshold_seconds}s"

    def test_tokenizer_cyrillic_performance(self) -> None:
        """Test tokenization of Cyrillic text."""
        tokenizer = Tokenizer()

        def tokenize_cyrillic():
            tokenizer.tokenize("коррупция взятка скандал политика новости")

        result = benchmark(
            tokenize_cyrillic,
            iterations=1000,
            threshold=TOKENIZER_THRESHOLD,
            name="Tokenizer - Cyrillic (1000x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Tokenizer too slow: {result.duration_seconds}s > {result.threshold_seconds}s"


class TestRankingPerformance:
    """Performance tests for the ranking service."""

    def test_ranking_small_dataset(self) -> None:
        """Test ranking of small dataset (100 posts)."""
        ranking_service = RankingService()
        posts = create_sample_posts(100)

        def rank_posts():
            ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        result = benchmark(
            rank_posts,
            iterations=100,
            threshold=RANKING_THRESHOLD,
            name="Ranking - 100 posts (100x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Ranking too slow: {result.duration_seconds}s > {result.threshold_seconds}s"

    def test_ranking_medium_dataset(self) -> None:
        """Test ranking of medium dataset (1000 posts)."""
        ranking_service = RankingService()
        posts = create_sample_posts(1000)

        def rank_posts():
            ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        result = benchmark(
            rank_posts,
            iterations=10,
            threshold=RANKING_THRESHOLD,
            name="Ranking - 1000 posts (10x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Ranking too slow: {result.duration_seconds}s > {result.threshold_seconds}s"

    def test_ranking_large_dataset(self) -> None:
        """Test ranking of large dataset (10000 posts)."""
        ranking_service = RankingService()
        posts = create_sample_posts(10000)

        def rank_posts():
            ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)

        result = benchmark(
            rank_posts,
            iterations=5,
            threshold=RANKING_THRESHOLD * 3,  # Allow more time for large dataset
            name="Ranking - 10000 posts (5x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Ranking too slow: {result.duration_seconds}s > {result.threshold_seconds}s"

    def test_recency_calculation_performance(self) -> None:
        """Test recency factor calculation performance."""
        ranking_service = RankingService()
        reference_time = datetime.now(timezone.utc)
        test_times = [
            reference_time - timedelta(hours=index)
            for index in range(1000)
        ]

        def calculate_recency():
            for posted_at in test_times:
                ranking_service.calculate_recency_factor(posted_at, reference_time)

        result = benchmark(
            calculate_recency,
            iterations=100,
            threshold=RECENCY_CALCULATION_THRESHOLD,
            name="Recency Calculation - 1000 times (100x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Recency calculation too slow: {result.duration_seconds}s"


class TestFormatterPerformance:
    """Performance tests for search result formatting."""

    def test_format_single_result(self) -> None:
        """Test formatting of single search result."""
        formatter = SearchFormatter()
        results = create_sample_search_results(1)

        def format_result():
            formatter.format_result(results[0], index=1)

        result = benchmark(
            format_result,
            iterations=1000,
            threshold=FORMATTER_THRESHOLD,
            name="Format Single Result (1000x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Formatting too slow: {result.duration_seconds}s"

    def test_format_results_page(self) -> None:
        """Test formatting of full results page."""
        formatter = SearchFormatter()
        results = create_sample_search_results(5)

        def format_page():
            formatter.format_results_page(
                query="test query",
                results=results,
                total_count=50,
                page=1,
                page_size=5,
            )

        result = benchmark(
            format_page,
            iterations=100,
            threshold=FORMATTER_THRESHOLD,
            name="Format Results Page (100x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Formatting too slow: {result.duration_seconds}s"

    def test_format_large_results_page(self) -> None:
        """Test formatting of page with maximum results."""
        formatter = SearchFormatter()
        results = create_sample_search_results(100)

        def format_page():
            formatter.format_results_page(
                query="test query with multiple keywords",
                results=results[:10],
                total_count=len(results),
                page=1,
                page_size=10,
            )

        result = benchmark(
            format_page,
            iterations=50,
            threshold=FORMATTER_THRESHOLD,
            name="Format Large Results Page (50x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Formatting too slow: {result.duration_seconds}s"


class TestSearchResponseTime:
    """
    End-to-end performance tests for search response time.

    Target: < 3 seconds (NFR-P-007)
    """

    def test_search_response_under_threshold(self) -> None:
        """Test that simulated search flow completes under 3 seconds."""
        # Simulate the full search flow:
        # 1. Tokenization
        # 2. Ranking
        # 3. Formatting

        tokenizer = Tokenizer()
        ranking_service = RankingService()
        formatter = SearchFormatter()

        # Simulate 1000 posts
        posts = create_sample_posts(1000)
        query = "corruption bribery scandal political investigation"

        def full_search_flow():
            # Step 1: Tokenize query
            keywords = tokenizer.tokenize(query)

            # Step 2: Rank results (simulating DB already returned results)
            ranked = ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)

            # Step 3: Convert to SearchResult format and format output
            results = [
                SearchResult(
                    post_id=str(post.post_id),
                    channel_id=str(uuid4()),
                    channel_username=f"channel_{index}",
                    channel_title=f"Channel {index}",
                    text_content="Sample content " * 10,
                    published_at=post.posted_at,
                    view_count=post.view_count,
                    reaction_score=post.reaction_score,
                    relative_engagement=post.relative_engagement,
                    telegram_message_id=10000 + index,
                )
                for index, post in enumerate(ranked[:100])
            ]

            # Step 4: Format for display
            formatter.format_results_page(
                query=query,
                results=results[:5],
                total_count=len(results),
                page=1,
                page_size=5,
            )

        result = benchmark(
            full_search_flow,
            iterations=10,
            threshold=SEARCH_RESPONSE_THRESHOLD,
            name="Full Search Flow (10x)",
        )

        print(f"\n{result}")
        assert result.passed, (
            f"Search response time exceeds threshold: "
            f"{result.duration_seconds}s > {SEARCH_RESPONSE_THRESHOLD}s"
        )

    def test_concurrent_search_simulation(self) -> None:
        """Test multiple concurrent search simulations."""
        tokenizer = Tokenizer()
        ranking_service = RankingService()
        formatter = SearchFormatter()

        posts = create_sample_posts(500)
        queries = [
            "corruption news",
            "political scandal",
            "breaking news",
            "investigation report",
            "economic crisis",
        ]

        def multiple_searches():
            for query in queries:
                keywords = tokenizer.tokenize(query)
                ranked = ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)

                results = [
                    SearchResult(
                        post_id=str(post.post_id),
                        channel_id=str(uuid4()),
                        channel_username=f"channel_{index}",
                        channel_title=f"Channel {index}",
                        text_content="Sample content " * 5,
                        published_at=post.posted_at,
                        view_count=post.view_count,
                        reaction_score=post.reaction_score,
                        relative_engagement=post.relative_engagement,
                        telegram_message_id=10000 + index,
                    )
                    for index, post in enumerate(ranked[:50])
                ]

                formatter.format_results_page(
                    query=query,
                    results=results[:5],
                    total_count=len(results),
                    page=1,
                    page_size=5,
                )

        result = benchmark(
            multiple_searches,
            iterations=5,
            threshold=SEARCH_RESPONSE_THRESHOLD * 2,
            name="5 Concurrent Searches (5x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Concurrent searches too slow: {result.duration_seconds}s"


class TestMemoryEfficiency:
    """Tests for memory-efficient operations."""

    def test_large_result_set_processing(self) -> None:
        """Test processing of large result sets without memory issues."""
        # Create large dataset
        posts = create_sample_posts(5000)

        ranking_service = RankingService()

        def process_large_set():
            ranked = ranking_service.rank_posts(posts, sort_mode=SortMode.COMBINED)
            # Process only top 100
            top_results = ranked[:100]
            return len(top_results)

        result = benchmark(
            process_large_set,
            iterations=10,
            threshold=RANKING_THRESHOLD * 3,
            name="Large Result Set (5000 posts, 10x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Large result set processing too slow: {result.duration_seconds}s"

    def test_incremental_result_building(self) -> None:
        """Test incremental building of results."""
        formatter = SearchFormatter()
        results = create_sample_search_results(100)

        def build_incrementally():
            # Simulate paginated access
            for page in range(1, 21):  # 20 pages
                start = (page - 1) * 5
                end = start + 5
                page_results = results[start:end] if end <= len(results) else results[start:]

                if page_results:
                    formatter.format_results_page(
                        query="test",
                        results=page_results,
                        total_count=len(results),
                        page=page,
                        page_size=5,
                    )

        result = benchmark(
            build_incrementally,
            iterations=20,
            threshold=FORMATTER_THRESHOLD * 2,
            name="Incremental Pagination (20 pages, 20x)",
        )

        print(f"\n{result}")
        assert result.passed, f"Incremental building too slow: {result.duration_seconds}s"


def run_all_benchmarks() -> list[BenchmarkResult]:
    """Run all benchmarks and return results."""
    results = []

    # Tokenizer benchmarks
    tokenizer = Tokenizer()

    results.append(benchmark(
        lambda: tokenizer.tokenize("corruption"),
        iterations=1000,
        threshold=TOKENIZER_THRESHOLD,
        name="Tokenizer - Single Word",
    ))

    results.append(benchmark(
        lambda: tokenizer.tokenize("corruption bribery scandal"),
        iterations=1000,
        threshold=TOKENIZER_THRESHOLD,
        name="Tokenizer - Multi Word",
    ))

    # Ranking benchmarks
    ranking_service = RankingService()
    posts_100 = create_sample_posts(100)
    posts_1000 = create_sample_posts(1000)

    results.append(benchmark(
        lambda: ranking_service.rank_posts(posts_100, SortMode.COMBINED),
        iterations=100,
        threshold=RANKING_THRESHOLD,
        name="Ranking - 100 posts",
    ))

    results.append(benchmark(
        lambda: ranking_service.rank_posts(posts_1000, SortMode.COMBINED),
        iterations=10,
        threshold=RANKING_THRESHOLD,
        name="Ranking - 1000 posts",
    ))

    # Formatter benchmarks
    formatter = SearchFormatter()
    search_results = create_sample_search_results(10)

    results.append(benchmark(
        lambda: formatter.format_results_page(
            query="test",
            results=search_results[:5],
            total_count=100,
            page=1,
            page_size=5,
        ),
        iterations=100,
        threshold=FORMATTER_THRESHOLD,
        name="Formatter - Results Page",
    ))

    return results


if __name__ == "__main__":
    print("Running TNSE Performance Benchmarks")
    print("=" * 60)

    results = run_all_benchmarks()

    print("\nBenchmark Results:")
    print("-" * 60)

    passed = 0
    failed = 0

    for result in results:
        print(result)
        if result.passed:
            passed += 1
        else:
            failed += 1

    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed")

    if failed > 0:
        exit(1)
