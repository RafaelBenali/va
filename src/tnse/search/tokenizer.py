"""
TNSE Tokenizer Module

Provides multi-language tokenization for Russian, English, and Ukrainian content
with Cyrillic normalization support.

Work Stream: WS-2.2 - Keyword Search Engine

Requirements addressed:
- REQ-NP-006: Handle Russian, English, Ukrainian, and other Cyrillic languages
- REQ-MO-005: Keyword-based search in metrics-only mode
"""

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional


# English stop words (common, high-frequency words with little semantic value)
ENGLISH_STOP_WORDS: set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has",
    "he", "in", "is", "it", "its", "of", "on", "or", "that", "the", "to",
    "was", "were", "will", "with", "the", "this", "but", "they", "have",
    "had", "what", "when", "where", "who", "which", "why", "how", "all",
    "each", "every", "both", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "can", "just", "should", "now", "over", "under", "again", "further",
    "then", "once", "here", "there", "any", "about", "out", "up", "down",
    "off", "between", "through", "during", "before", "after", "above",
    "below", "into", "if", "because", "until", "while", "you", "your",
    "we", "our", "my", "me", "him", "her", "them", "do", "does", "did",
    "been", "being", "would", "could", "am",
}

# Russian stop words
RUSSIAN_STOP_WORDS: set[str] = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а",
    "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же",
    "вы", "за", "бы", "по", "только", "её", "ее", "мне", "было", "вот",
    "от", "меня", "ещё", "еще", "нет", "о", "из", "ему", "теперь",
    "когда", "уже", "вам", "ни", "быть", "был", "была", "были", "есть",
    "надо", "это", "этот", "эта", "эти", "мой", "моя", "мое", "мои",
    "тоже", "себя", "своей", "свою", "своих", "ей", "им", "них", "их",
    "для", "при", "между", "через", "над", "под", "без", "до", "после",
    "перед", "около", "также", "можно", "нужно", "чтобы", "если", "или",
    "либо", "ли", "потому", "поэтому", "тут", "там", "здесь", "тогда",
}

# Ukrainian stop words
UKRAINIAN_STOP_WORDS: set[str] = {
    "i", "та", "не", "що", "вiн", "вона", "на", "я", "з", "як", "а", "але",
    "то", "все", "так", "його", "але", "ти", "у", "же", "ви", "за", "по",
    "тiльки", "її", "мені", "було", "ось", "від", "мене", "ще", "ні",
    "немає", "про", "з", "йому", "тепер", "коли", "вже", "вам", "бути",
    "був", "була", "були", "є", "треба", "це", "цей", "ця", "ці", "мій",
    "моя", "моє", "мої", "також", "себе", "своєї", "свою", "своїх", "їй",
    "їм", "них", "їх", "для", "при", "між", "через", "над", "під", "без",
    "до", "після", "перед", "біля", "можна", "потрібно", "щоб", "якщо",
    "або", "чи", "тому", "тут", "там", "тоді", "і",
}

# Combined stop words set
ALL_STOP_WORDS: set[str] = ENGLISH_STOP_WORDS | RUSSIAN_STOP_WORDS | UKRAINIAN_STOP_WORDS


@dataclass
class Tokenizer:
    """Multi-language tokenizer with Cyrillic normalization support.

    Provides tokenization for Russian, English, and Ukrainian text with:
    - Lowercase normalization
    - Punctuation removal
    - Optional stop word removal
    - Optional number removal
    - Minimum token length filtering
    - Cyrillic character normalization (e.g., Russian 'yo' variants)

    Attributes:
        min_token_length: Minimum length for tokens to be included (default: 2)
        remove_stop_words: Whether to remove stop words (default: True)
        remove_numbers: Whether to remove numeric tokens (default: False)
    """

    min_token_length: int = 2
    remove_stop_words: bool = True
    remove_numbers: bool = False

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into a list of normalized tokens.

        Performs the following operations:
        1. Normalize Cyrillic characters
        2. Convert to lowercase
        3. Split on whitespace and punctuation
        4. Filter by minimum length
        5. Optionally remove stop words
        6. Optionally remove numbers

        Args:
            text: The input text to tokenize.

        Returns:
            A list of normalized tokens.
        """
        if not text or not text.strip():
            return []

        # Normalize Cyrillic characters
        normalized_text = self._normalize_cyrillic(text)

        # Convert to lowercase
        normalized_text = normalized_text.lower()

        # Split on whitespace and punctuation
        tokens = self._split_text(normalized_text)

        # Filter tokens
        filtered_tokens = []
        for token in tokens:
            # Skip empty tokens
            if not token:
                continue

            # Skip tokens that are too short
            if len(token) < self.min_token_length:
                continue

            # Skip numbers if configured
            if self.remove_numbers and self._is_number(token):
                continue

            # Skip stop words if configured
            if self.remove_stop_words and token in ALL_STOP_WORDS:
                continue

            filtered_tokens.append(token)

        return filtered_tokens

    def _normalize_cyrillic(self, text: str) -> str:
        """Normalize Cyrillic text for consistent searching.

        Handles:
        - Russian 'yo' letter variants (e -> e)
        - Unicode normalization (NFC form)

        Args:
            text: The input text to normalize.

        Returns:
            Normalized text.
        """
        # Apply Unicode NFC normalization
        text = unicodedata.normalize("NFC", text)

        # Normalize Russian 'yo' to 'ye' for consistent matching
        # Both forms should match the same content
        text = text.replace("\u0451", "\u0435")  # lowercase yo -> ye
        text = text.replace("\u0401", "\u0415")  # uppercase Yo -> Ye

        return text

    def _split_text(self, text: str) -> list[str]:
        """Split text into tokens on whitespace and punctuation.

        Args:
            text: The input text to split.

        Returns:
            A list of tokens.
        """
        # Split on whitespace and punctuation using regex
        # The \p{P} and \p{S} patterns require regex module, so use simpler approach
        # Use a pattern that matches word characters in any language
        tokens = []
        current_token = []

        for char in text:
            # Check if character is a word character (letter, digit, or underscore)
            if char.isalnum() or char == "_":
                current_token.append(char)
            else:
                # Non-word character - end current token if exists
                if current_token:
                    tokens.append("".join(current_token))
                    current_token = []

        # Don't forget the last token
        if current_token:
            tokens.append("".join(current_token))

        return tokens

    def _is_number(self, token: str) -> bool:
        """Check if a token is purely numeric.

        Args:
            token: The token to check.

        Returns:
            True if the token is a number, False otherwise.
        """
        # Check if token consists only of digits
        return token.isdigit()
