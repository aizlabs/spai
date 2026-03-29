"""
Generate and validate glossary entries after the article text is approved.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Dict, List

import spacy
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from scripts import prompts
from scripts.config import AppConfig
from scripts.llm_factory import create_chat_model, with_structured_output
from scripts.models import AdaptedArticle, VocabularyItem, coerce_vocabulary_items
from scripts.text_utils import (
    ensure_vocabulary_bolded,
    normalize_existing_vocabulary_bolding,
    normalize_vocabulary_term,
    vocabulary_term_present,
)

REJECT_ENTITY_LABELS = {"PER", "PERSON", "GPE", "LOC"}
COMMON_PLACE_TERMS = {
    "alemania",
    "america latina",
    "barcelona",
    "china",
    "dinamarca",
    "donald trump",
    "espana",
    "estados unidos",
    "europa",
    "iran",
    "israel",
    "madrid",
    "mexico",
    "rusia",
    "teheran",
    "ucrania",
    "venezuela",
    "washington",
    "yemen",
}
SPANISH_STOPWORDS = {
    "a",
    "al",
    "con",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "lo",
    "los",
    "para",
    "por",
    "su",
    "sus",
    "un",
    "una",
    "unos",
    "unas",
    "y",
}
ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "of",
    "or",
    "the",
    "to",
}
COGNATE_SUFFIX_MAP = (
    ("aciones", "ations"),
    ("acion", "ation"),
    ("ciones", "tions"),
    ("cion", "tion"),
    ("siones", "sions"),
    ("sion", "sion"),
    ("dades", "ties"),
    ("dad", "ty"),
    ("mente", "ly"),
    ("ismos", "isms"),
    ("ismo", "ism"),
    ("istas", "ists"),
    ("ista", "ist"),
    ("ivos", "ives"),
    ("ivo", "ive"),
    ("ivas", "ives"),
    ("iva", "ive"),
    ("icos", "ic"),
    ("icas", "ic"),
    ("ico", "ic"),
    ("ica", "ic"),
    ("arios", "ary"),
    ("arias", "ary"),
    ("ario", "ary"),
    ("aria", "ary"),
    ("ables", "able"),
    ("able", "able"),
    ("ibles", "ible"),
    ("ible", "ible"),
    ("osas", "ous"),
    ("osos", "ous"),
    ("osa", "ous"),
    ("oso", "ous"),
    ("ales", "al"),
    ("al", "al"),
)
ADJECTIVE_SUFFIXES = (
    "al",
    "ales",
    "aria",
    "arias",
    "ario",
    "arios",
    "ible",
    "ibles",
    "ica",
    "icas",
    "ico",
    "icos",
    "iva",
    "ivas",
    "ivo",
    "ivos",
    "oria",
    "orio",
    "sible",
    "taria",
    "tario",
)


class GlossaryResponse(BaseModel):
    """Structured LLM output for glossary generation."""

    vocabulary: List[VocabularyItem] = Field(default_factory=list)


class GlossaryGenerator:
    """Generate glossary entries from the final approved article text."""

    def __init__(self, config: AppConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger.getChild("GlossaryGenerator")
        self.llm_config = config.llm.model_dump()
        self.temperature = min(self.llm_config.get("temperature", 0.3), 0.2)
        self._nlp = None
        self._init_chain()
        self._init_nlp()

    def generate(self, article: AdaptedArticle) -> List[VocabularyItem]:
        """Generate glossary candidates from the final approved text."""
        prompt = prompts.get_glossary_generation_prompt(article)
        response = self._call_llm(prompt)
        return coerce_vocabulary_items(response.model_dump().get("vocabulary") or [])

    def validate(
        self,
        content: str,
        vocabulary: List[VocabularyItem],
    ) -> tuple[List[VocabularyItem], Dict[str, str]]:
        """Filter glossary candidates using deterministic learner-focused rules."""
        accepted: List[VocabularyItem] = []
        dropped: Dict[str, str] = {}
        seen_terms = set()
        doc = self._analyze_content(content)

        for raw_item in vocabulary:
            term = normalize_vocabulary_term(raw_item.term)
            english = raw_item.english.strip()
            explanation = raw_item.explanation.strip()
            display_term = term or raw_item.term or "<empty>"

            if not term or not english or not explanation:
                dropped[display_term] = "missing required glossary fields"
                continue

            normalized_key = term.casefold()
            if normalized_key in seen_terms:
                dropped[display_term] = "duplicate term"
                continue

            if not vocabulary_term_present(content, term):
                dropped[display_term] = "term not present literally in article text"
                continue

            if self._is_rejected_named_entity(doc, term, english):
                dropped[display_term] = "named entity or common place/person name"
                continue

            if self._is_transparent_term(term, english):
                dropped[display_term] = "transparent term for English-speaking learners"
                continue

            if self._is_isolated_modifier(doc, content, term):
                dropped[display_term] = "isolated modifier instead of the full phrase"
                continue

            accepted.append(
                VocabularyItem(
                    term=term,
                    english=english,
                    explanation=explanation,
                )
            )
            seen_terms.add(normalized_key)

        return accepted, dropped

    def apply_bolding(self, content: str, vocabulary: List[VocabularyItem]) -> str:
        """Bold accepted glossary terms in the final article text."""
        if not vocabulary:
            return content

        term_map = {item.term: item.english or item.explanation for item in vocabulary}
        cleaned_content = content.replace("**", "")
        cleaned_content = normalize_existing_vocabulary_bolding(cleaned_content, term_map)
        return ensure_vocabulary_bolded(cleaned_content, term_map)

    def enrich_article(self, article: AdaptedArticle) -> AdaptedArticle:
        """Attach a validated glossary to an approved article without blocking publication."""
        try:
            candidates = self.generate(article)
            accepted, dropped = self.validate(article.content, candidates)

            if dropped:
                self.logger.warning(
                    "Dropped glossary terms for article '%s': %s",
                    article.title,
                    ", ".join(f"{term} ({reason})" for term, reason in dropped.items()),
                )

            if not accepted:
                self.logger.info(
                    "No glossary entries survived validation for '%s'; publishing text without glossary",
                    article.title,
                )
                return article.model_copy(update={"vocabulary": []})

            content = self.apply_bolding(article.content, accepted)
            self.logger.info(
                "Accepted %s glossary entries for '%s'",
                len(accepted),
                article.title,
            )
            return article.model_copy(update={"content": content, "vocabulary": accepted})
        except Exception as exc:
            self.logger.error(
                "Glossary generation failed for '%s': %s. Publishing without glossary.",
                article.title,
                exc,
            )
            return article.model_copy(update={"vocabulary": []})

    def _init_chain(self) -> None:
        model_name = self.llm_config["models"].get(
            "adaptation",
            self.llm_config["models"]["generation"],
        )
        chat_model = create_chat_model(self.llm_config, model_name, self.temperature)
        structured_llm = with_structured_output(chat_model, GlossaryResponse)
        self.prompt_template = ChatPromptTemplate.from_messages([("user", "{prompt}")])
        self.chain = self.prompt_template | structured_llm

    def _init_nlp(self) -> None:
        try:
            self._nlp = spacy.load("es_core_news_sm")
        except Exception as exc:
            self.logger.warning(
                "SpaCy model unavailable for glossary validation; falling back to lightweight rules: %s",
                exc,
            )
            self._nlp = None

    def _call_llm(self, prompt: str) -> BaseModel:
        return self.chain.invoke({"prompt": prompt})

    def _analyze_content(self, content: str):
        if self._nlp is None:
            return None
        return self._nlp(content)

    def _is_rejected_named_entity(self, doc, term: str, english: str) -> bool:
        folded_term = self._fold_text(term)
        if folded_term in COMMON_PLACE_TERMS:
            return True

        if english and term == english and self._looks_like_title_case_name(term):
            return True

        if doc is None:
            return False

        for span in self._find_matching_spans(doc, term):
            for ent in doc.ents:
                if ent.start <= span.start and span.end <= ent.end:
                    if ent.label_ in REJECT_ENTITY_LABELS:
                        return True
        return False

    def _is_transparent_term(self, term: str, english: str) -> bool:
        spanish_tokens = [
            token
            for token in self._tokenize(term)
            if token not in SPANISH_STOPWORDS and len(token) >= 4
        ]
        english_tokens = [
            token
            for token in self._tokenize(english)
            if token not in ENGLISH_STOPWORDS and len(token) >= 4
        ]

        if not spanish_tokens or not english_tokens:
            return False

        matches = 0
        for spanish_token in spanish_tokens:
            if any(self._tokens_look_transparent(spanish_token, english_token) for english_token in english_tokens):
                matches += 1

        return matches >= len(spanish_tokens)

    def _is_isolated_modifier(self, doc, content: str, term: str) -> bool:
        stripped_term = term.strip()
        if " " in stripped_term:
            return False

        if doc is None:
            folded_term = self._fold_text(stripped_term)
            if not any(folded_term.endswith(suffix) for suffix in ADJECTIVE_SUFFIXES):
                return False
            phrase_pattern = re.compile(
                rf"(?<!\w)\w+\s+{re.escape(stripped_term)}(?!\w)|(?<!\w){re.escape(stripped_term)}\s+\w+(?!\w)",
                re.IGNORECASE,
            )
            return bool(phrase_pattern.search(content))

        for span in self._find_matching_spans(doc, term):
            if len(span) != 1:
                continue
            token = span[0]
            if token.pos_ == "ADJ":
                return True
        return False

    def _find_matching_spans(self, doc, term: str):
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.IGNORECASE)
        matches = []
        for match in pattern.finditer(doc.text):
            span = doc.char_span(match.start(), match.end(), alignment_mode="expand")
            if span is None:
                continue
            if span.text.strip().casefold() != term.casefold():
                continue
            matches.append(span)
        return matches

    def _tokenize(self, text: str) -> List[str]:
        folded = self._fold_text(text)
        return re.findall(r"[a-z]+", folded)

    def _fold_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        return without_accents.casefold()

    def _tokens_look_transparent(self, spanish_token: str, english_token: str) -> bool:
        if spanish_token == english_token:
            return True

        singular_spanish = self._singularize(spanish_token)
        singular_english = self._singularize(english_token)
        if singular_spanish == singular_english:
            return True

        transformed = self._apply_cognate_suffix_map(singular_spanish)
        if transformed == singular_english:
            return True

        return False

    def _apply_cognate_suffix_map(self, token: str) -> str:
        for source_suffix, target_suffix in COGNATE_SUFFIX_MAP:
            if token.endswith(source_suffix):
                return f"{token[:-len(source_suffix)]}{target_suffix}"
        return token

    def _singularize(self, token: str) -> str:
        if token.endswith("es") and len(token) > 4:
            return token[:-2]
        if token.endswith("s") and len(token) > 3:
            return token[:-1]
        return token

    def _looks_like_title_case_name(self, text: str) -> bool:
        parts = [part for part in text.split() if part]
        if not parts:
            return False
        return len(parts) >= 2 and all(part[:1].isupper() for part in parts)
