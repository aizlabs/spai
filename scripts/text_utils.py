"""
Text utilities for the pipeline.

Includes vocabulary normalization, presence checks, and bold marking used after
level adaptation.
"""

from typing import Dict


def _is_word_char(c: str) -> bool:
    """True if c is alphanumeric or underscore (part of a token)."""
    return len(c) == 1 and (c.isalnum() or c == "_")


def _term_at_word_boundary(content: str, start: int, term: str) -> bool:
    """
    True if content[start:start+len(term)] equals term and is a whole word.

    Whole word: not preceded and not followed by a word character (so we do
    not bold "tasa" inside "tasas" or "año" inside "años").
    """
    if not content[start:].startswith(term):
        return False
    end = start + len(term)
    if start > 0 and _is_word_char(content[start - 1]):
        return False
    if end < len(content) and _is_word_char(content[end]):
        return False
    return True


def normalize_vocabulary_term(term: str) -> str:
    """
    Normalize a glossary term to plain text.

    Terms are trimmed and repeatedly stripped of wrapping markdown bold markers,
    so values like "**término**" and "****término****" are stored as "término".
    Internal punctuation and accents are preserved.
    """
    normalized = term.strip()

    while len(normalized) >= 4 and normalized.startswith("**") and normalized.endswith("**"):
        normalized = normalized[2:-2].strip()

    return normalized


def vocabulary_term_present(content: str, term: str) -> bool:
    """
    Return True if term appears literally in content as a whole word or phrase.

    This exact-match check works for both plain and markdown-bolded terms because
    the surrounding `**` markers are treated as non-word characters.
    """
    if not term:
        return False

    max_start = len(content) - len(term)
    for start in range(max_start + 1):
        if _term_at_word_boundary(content, start, term):
            return True

    return False


def filter_vocabulary_to_content(
    content: str,
    vocabulary: Dict[str, str],
) -> tuple[Dict[str, str], list[str]]:
    """
    Keep only glossary entries whose terms appear literally in content.

    Returns:
        A tuple of (filtered_vocabulary, dropped_terms).
    """
    filtered: Dict[str, str] = {}
    dropped: list[str] = []

    for term, gloss in vocabulary.items():
        if vocabulary_term_present(content, term):
            filtered[term] = gloss
        else:
            dropped.append(term)

    return filtered, dropped


def ensure_vocabulary_bolded(content: str, vocabulary: Dict[str, str]) -> str:
    """
    Ensure every vocabulary term appears bolded in content.

    Single-pass FSA: track position and inside_bold state. When we see '**',
    toggle inside_bold. When not inside_bold, if content at current position
    starts with any term (longest first) at a word boundary, wrap it in **
    and advance by term length. Otherwise emit one character and advance.

    Terms are matched on word boundaries only (no prefix match): e.g. "tasa"
    in "las tasas suben" is not bolded, to avoid corrupting inflected/derived
    forms and to keep glossed terms in their original form.

    Args:
        content: Article body (may already contain some **bold** terms).
        vocabulary: Glossary dict (keys = Spanish terms to bold).

    Returns:
        Content with every vocabulary term wrapped in ** when not already bolded.
    """
    if not vocabulary:
        return content

    # Terms sorted by length descending so longer phrases match before substrings
    terms = sorted(
        (t for t in vocabulary if t),
        key=len,
        reverse=True,
    )
    if not terms:
        return content

    i = 0
    inside_bold = False
    result: list[str] = []

    while i < len(content):
        if i + 2 <= len(content) and content[i : i + 2] == "**":
            result.append("**")
            inside_bold = not inside_bold
            i += 2
            continue

        if not inside_bold:
            matched = False
            for term in terms:
                if _term_at_word_boundary(content, i, term):
                    result.append("**")
                    result.append(term)
                    result.append("**")
                    i += len(term)
                    matched = True
                    break
            if matched:
                continue

        result.append(content[i])
        i += 1

    return "".join(result)
