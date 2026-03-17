"""
Text utilities for the pipeline.

Includes vocabulary bold marking (FSA-based) used after level adaptation.
"""

from typing import Dict


def ensure_vocabulary_bolded(content: str, vocabulary: Dict[str, str]) -> str:
    """
    Ensure every vocabulary term appears bolded in content.

    Single-pass FSA: track position and inside_bold state. When we see '**',
    toggle inside_bold. When not inside_bold, if content at current position
    starts with any term (longest first), wrap it in ** and advance by term
    length. Otherwise emit one character and advance.

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
                if content[i:].startswith(term):
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
