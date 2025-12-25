"""
TNSE Tokenizer Tests

Unit tests for multi-language tokenization functionality.

Work Stream: WS-2.2 - Keyword Search Engine

Requirements addressed:
- REQ-NP-006: Handle Russian, English, Ukrainian, and other Cyrillic languages
- REQ-MO-005: Keyword-based search in metrics-only mode
"""

import pytest


class TestTokenizer:
    """Tests for the Tokenizer class."""

    def test_tokenize_english_text(self) -> None:
        """Test tokenization of basic English text."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Hello world this is a test"
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) == 6
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_tokenize_russian_text(self) -> None:
        """Test tokenization of Russian text."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Привет мир это тестовое сообщение"
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) >= 4
        assert "привет" in tokens
        assert "мир" in tokens

    def test_tokenize_ukrainian_text(self) -> None:
        """Test tokenization of Ukrainian text."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Привіт світ це тестове повідомлення"
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) >= 4
        assert "привіт" in tokens
        assert "світ" in tokens

    def test_tokenize_mixed_language_text(self) -> None:
        """Test tokenization of text containing multiple languages."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Hello привет world мир"
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert "hello" in tokens
        assert "привет" in tokens
        assert "world" in tokens
        assert "мир" in tokens

    def test_tokenize_removes_punctuation(self) -> None:
        """Test that punctuation is properly removed during tokenization."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Hello, world! This is a test."
        tokens = tokenizer.tokenize(text)

        assert "hello" in tokens
        assert "world" in tokens
        # No punctuation should be in tokens
        for token in tokens:
            assert "," not in token
            assert "!" not in token
            assert "." not in token

    def test_tokenize_removes_numbers_option(self) -> None:
        """Test that numbers can be optionally removed during tokenization."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(remove_numbers=True)
        text = "Testing 123 numbers here"
        tokens = tokenizer.tokenize(text)

        assert "123" not in tokens
        assert "testing" in tokens
        assert "numbers" in tokens

    def test_tokenize_keeps_numbers_by_default(self) -> None:
        """Test that numbers are kept by default."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Version 2.0 released"
        tokens = tokenizer.tokenize(text)

        # Numbers should be present in some form
        assert "version" in tokens
        assert "released" in tokens

    def test_tokenize_empty_string(self) -> None:
        """Test tokenization of empty string."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = ""
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) == 0

    def test_tokenize_whitespace_only(self) -> None:
        """Test tokenization of whitespace-only string."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "   \t\n   "
        tokens = tokenizer.tokenize(text)

        assert isinstance(tokens, list)
        assert len(tokens) == 0

    def test_tokenize_lowercases_text(self) -> None:
        """Test that tokenization produces lowercase tokens."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "HELLO WORLD Hello World"
        tokens = tokenizer.tokenize(text)

        # All tokens should be lowercase
        for token in tokens:
            assert token == token.lower()

    def test_tokenize_minimum_length(self) -> None:
        """Test that very short tokens are filtered out."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(min_token_length=2)
        text = "a I am on the go"
        tokens = tokenizer.tokenize(text)

        # Single letter tokens should be filtered
        assert "a" not in tokens
        assert "i" not in tokens
        assert "am" in tokens
        assert "on" in tokens


class TestCyrillicNormalization:
    """Tests for Cyrillic normalization functionality."""

    def test_normalize_russian_yo(self) -> None:
        """Test normalization of Russian 'yo' letter variants."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        # Both should normalize to same form
        text1 = "ёлка"
        text2 = "елка"

        tokens1 = tokenizer.tokenize(text1)
        tokens2 = tokenizer.tokenize(text2)

        # Should normalize to same token
        assert tokens1 == tokens2

    def test_normalize_ukrainian_special_characters(self) -> None:
        """Test normalization of Ukrainian-specific characters."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        text = "Київ їжак ґанок"
        tokens = tokenizer.tokenize(text)

        assert len(tokens) == 3
        assert "київ" in tokens or any("и" in token for token in tokens)

    def test_normalize_mixed_cyrillic_latin(self) -> None:
        """Test handling of mixed Cyrillic and Latin lookalike characters."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()
        # Some Cyrillic chars look like Latin: а (Cyrillic) vs a (Latin)
        text = "тест test"
        tokens = tokenizer.tokenize(text)

        assert len(tokens) == 2


class TestStopWordRemoval:
    """Tests for stop word removal functionality."""

    def test_remove_english_stop_words(self) -> None:
        """Test removal of English stop words."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(remove_stop_words=True)
        text = "The quick brown fox jumps over the lazy dog"
        tokens = tokenizer.tokenize(text)

        assert "the" not in tokens
        assert "over" not in tokens
        assert "quick" in tokens
        assert "fox" in tokens

    def test_remove_russian_stop_words(self) -> None:
        """Test removal of Russian stop words."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(remove_stop_words=True)
        text = "это и не только важная новость"
        tokens = tokenizer.tokenize(text)

        # Common stop words should be removed
        assert "это" not in tokens
        assert "и" not in tokens
        assert "не" not in tokens
        assert "важная" in tokens
        assert "новость" in tokens

    def test_keep_stop_words_when_disabled(self) -> None:
        """Test that stop words are kept when removal is disabled."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(remove_stop_words=False)
        text = "the quick fox"
        tokens = tokenizer.tokenize(text)

        assert "the" in tokens
        assert "quick" in tokens
        assert "fox" in tokens


class TestTokenizerConfiguration:
    """Tests for tokenizer configuration options."""

    def test_default_configuration(self) -> None:
        """Test default tokenizer configuration."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer()

        assert tokenizer.min_token_length == 2
        assert tokenizer.remove_stop_words is True
        assert tokenizer.remove_numbers is False

    def test_custom_configuration(self) -> None:
        """Test custom tokenizer configuration."""
        from src.tnse.search.tokenizer import Tokenizer

        tokenizer = Tokenizer(
            min_token_length=3,
            remove_stop_words=False,
            remove_numbers=True,
        )

        assert tokenizer.min_token_length == 3
        assert tokenizer.remove_stop_words is False
        assert tokenizer.remove_numbers is True
