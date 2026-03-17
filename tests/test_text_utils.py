"""
Unit tests for text_utils.ensure_vocabulary_bolded (FSA vocabulary bold marking).
"""

import pytest
from scripts.text_utils import ensure_vocabulary_bolded


class TestEnsureVocabularyBoldedBasic:
    """Basic unit tests for the helper."""

    def test_empty_vocabulary_returns_content_unchanged(self):
        assert ensure_vocabulary_bolded("la tasa sube", {}) == "la tasa sube"

    def test_term_already_bolded_unchanged(self):
        assert (
            ensure_vocabulary_bolded("la **tasa** sube", {"tasa": "rate"})
            == "la **tasa** sube"
        )

    def test_term_not_bolded_gets_wrapped(self):
        assert (
            ensure_vocabulary_bolded("la tasa sube", {"tasa": "rate"})
            == "la **tasa** sube"
        )

    def test_two_terms_longer_first(self):
        vocab = {"tasa de desempleo": "unemployment rate", "tasa": "rate"}
        content = "La tasa de desempleo y la tasa suben."
        got = ensure_vocabulary_bolded(content, vocab)
        assert got == "La **tasa de desempleo** y la **tasa** suben."

    def test_term_with_special_chars_exact_match(self):
        content = "El índice (IPC) sube."
        vocab = {"índice (IPC)": "index (CPI)"}
        assert (
            ensure_vocabulary_bolded(content, vocab)
            == "El **índice (IPC)** sube."
        )


class TestEnsureVocabularyBoldedEdgeCases:
    """Tricky edge cases (FSA and string match)."""

    def test_empty_content_returns_empty_string(self):
        assert ensure_vocabulary_bolded("", {"tasa": "rate"}) == ""

    def test_vocabulary_with_empty_string_key_skipped(self):
        # Should not advance by 0 (infinite loop); empty key skipped
        content = "la tasa sube"
        vocab = {"": "nope", "tasa": "rate"}
        assert ensure_vocabulary_bolded(content, vocab) == "la **tasa** sube"

    def test_term_only_inside_already_bold_span_unchanged(self):
        content = "**la tasa sube**"
        vocab = {"tasa": "rate"}
        assert ensure_vocabulary_bolded(content, vocab) == "**la tasa sube**"

    def test_term_appears_both_bolded_and_plain(self):
        content = "La **tasa** y la tasa suben."
        vocab = {"tasa": "rate"}
        assert (
            ensure_vocabulary_bolded(content, vocab)
            == "La **tasa** y la **tasa** suben."
        )

    def test_four_asterisks_toggles_state_correctly(self):
        content = "****"
        vocab = {}
        assert ensure_vocabulary_bolded(content, vocab) == "****"

    def test_consecutive_bold_markers_no_erroneous_match(self):
        content = "**a** **b**"
        vocab = {"a": "x"}
        # 'a' is inside bold, so not wrapped again
        assert ensure_vocabulary_bolded(content, vocab) == "**a** **b**"

    def test_unclosed_bold_no_wrap_inside(self):
        content = "**tasa sube"
        vocab = {"tasa": "rate"}
        # We are inside_bold after **, so "tasa" is not wrapped
        assert ensure_vocabulary_bolded(content, vocab) == "**tasa sube"

    def test_term_as_prefix_of_longer_word_prefix_match(self):
        content = "las tasas suben"
        vocab = {"tasa": "rate"}
        # Current spec: starts with term → wrap (prefix match)
        assert (
            ensure_vocabulary_bolded(content, vocab)
            == "las **tasa**s suben"
        )

    def test_unicode_accents_prefix_match(self):
        content = "años"
        vocab = {"año": "year"}
        assert ensure_vocabulary_bolded(content, vocab) == "**año**s"

    def test_unicode_accents_separate_word(self):
        content = "el año pasado"
        vocab = {"año": "year"}
        assert ensure_vocabulary_bolded(content, vocab) == "el **año** pasado"

    def test_content_starts_with_term(self):
        content = "tasa sube"
        vocab = {"tasa": "rate"}
        assert ensure_vocabulary_bolded(content, vocab) == "**tasa** sube"

    def test_content_ends_with_term(self):
        content = "sube la tasa"
        vocab = {"tasa": "rate"}
        assert ensure_vocabulary_bolded(content, vocab) == "sube la **tasa**"

    def test_term_longer_than_content_no_match(self):
        content = "ab"
        vocab = {"abcd": "x"}
        assert ensure_vocabulary_bolded(content, vocab) == "ab"

    def test_nested_terms_longest_first_phrase_only(self):
        content = "la tasa de desempleo sube"
        vocab = {"tasa de desempleo": "unemployment rate", "tasa": "rate"}
        assert (
            ensure_vocabulary_bolded(content, vocab)
            == "la **tasa de desempleo** sube"
        )

    def test_nested_terms_short_only_when_long_not_present(self):
        content = "la tasa sube"
        vocab = {"tasa de desempleo": "unemployment rate", "tasa": "rate"}
        assert (
            ensure_vocabulary_bolded(content, vocab)
            == "la **tasa** sube"
        )
