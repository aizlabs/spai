from unittest.mock import MagicMock

import pytest

from scripts.glossary_generator import GlossaryGenerator
from scripts.models import VocabularyItem


@pytest.fixture
def glossary_generator(monkeypatch, base_config, mock_logger):
    monkeypatch.setattr(GlossaryGenerator, "_init_chain", lambda self: None)
    monkeypatch.setattr(GlossaryGenerator, "_init_nlp", lambda self: setattr(self, "_nlp", None))
    return GlossaryGenerator(base_config, mock_logger)


def test_validate_rejects_named_entities_transparent_terms_and_fragments(glossary_generator):
    content = (
        "Irán lanzó bombardeos con drones. Donald Trump habló con Estados Unidos sobre Israel. "
        "La política migratoria cambió. También hubo decisiones unilaterales."
    )
    candidates = [
        VocabularyItem(term="Irán", english="Iran", explanation="país en el Medio Oriente"),
        VocabularyItem(
            term="Estados Unidos",
            english="United States",
            explanation="país en América del Norte",
        ),
        VocabularyItem(
            term="Donald Trump",
            english="Donald Trump",
            explanation="expresidente de Estados Unidos",
        ),
        VocabularyItem(term="drones", english="drones", explanation="aviones no tripulados"),
        VocabularyItem(
            term="migratoria",
            english="migratory",
            explanation="relacionada con el movimiento de personas entre países",
        ),
        VocabularyItem(
            term="unilaterales",
            english="unilateral",
            explanation="hechas por un solo lado",
        ),
    ]

    accepted, dropped = glossary_generator.validate(content, candidates)

    assert accepted == []
    assert set(dropped) == {
        "Irán",
        "Estados Unidos",
        "Donald Trump",
        "drones",
        "migratoria",
        "unilaterales",
    }


def test_validate_keeps_high_value_terms_and_context_phrases(glossary_generator):
    content = (
        "Los bombardeos aumentaron en la región. Los ayatolás criticaron la respuesta. "
        "La Guardia Revolucionaria movilizó más tropas. Los hutíes apoyaron la operación. "
        "La política migratoria cambió después del acuerdo."
    )
    candidates = [
        VocabularyItem(
            term="bombardeos",
            english="bombings",
            explanation="ataques con bombas desde el aire",
        ),
        VocabularyItem(
            term="ayatolás",
            english="ayatollahs",
            explanation="líderes religiosos en Irán",
        ),
        VocabularyItem(
            term="Guardia Revolucionaria",
            english="Revolutionary Guard",
            explanation="fuerza militar de élite en Irán",
        ),
        VocabularyItem(
            term="hutíes",
            english="Houthis",
            explanation="grupo rebelde en Yemen",
        ),
        VocabularyItem(
            term="política migratoria",
            english="migration policy",
            explanation="reglas del gobierno sobre la inmigración",
        ),
    ]

    accepted, dropped = glossary_generator.validate(content, candidates)

    assert [item.term for item in accepted] == [
        "bombardeos",
        "ayatolás",
        "Guardia Revolucionaria",
        "hutíes",
        "política migratoria",
    ]
    assert dropped == {}


def test_validate_without_nlp_rejects_people_and_places_but_keeps_organizations(glossary_generator):
    content = (
        "Pedro Sánchez habló con Francia y París. "
        "La Guardia Revolucionaria respondió después."
    )
    candidates = [
        VocabularyItem(
            term="Pedro Sánchez",
            english="Pedro Sanchez",
            explanation="presidente del gobierno de España",
        ),
        VocabularyItem(
            term="Francia",
            english="France",
            explanation="país europeo",
        ),
        VocabularyItem(
            term="París",
            english="Paris",
            explanation="capital de Francia",
        ),
        VocabularyItem(
            term="Guardia Revolucionaria",
            english="Revolutionary Guard",
            explanation="fuerza militar de élite en Irán",
        ),
    ]

    accepted, dropped = glossary_generator.validate(content, candidates)

    assert [item.term for item in accepted] == ["Guardia Revolucionaria"]
    assert dropped["Pedro Sánchez"] == "named entity or common place/person name"
    assert dropped["Francia"] == "named entity or common place/person name"
    assert dropped["París"] == "named entity or common place/person name"


def test_apply_bolding_marks_only_accepted_terms(glossary_generator):
    content = "La política migratoria cambió después de los bombardeos."
    items = [
        VocabularyItem(
            term="política migratoria",
            english="migration policy",
            explanation="reglas del gobierno sobre la inmigración",
        ),
        VocabularyItem(
            term="bombardeos",
            english="bombings",
            explanation="ataques con bombas desde el aire",
        ),
    ]

    bolded = glossary_generator.apply_bolding(content, items)

    assert "**política migratoria**" in bolded
    assert "**bombardeos**" in bolded


def test_isolated_modifier_allows_predicative_adjectives_with_nlp(glossary_generator):
    class FakeHead:
        def __init__(self, pos_):
            self.pos_ = pos_

    class FakeToken:
        def __init__(self, pos_, dep_, head_pos_):
            self.pos_ = pos_
            self.dep_ = dep_
            self.head = FakeHead(head_pos_)

    predicative = [FakeToken("ADJ", "ROOT", "VERB")]
    attributive = [FakeToken("ADJ", "amod", "NOUN")]

    glossary_generator._find_matching_spans = MagicMock(
        side_effect=[[[predicative[0]]], [[attributive[0]]]]
    )

    assert glossary_generator._is_isolated_modifier(object(), "El sistema es frágil.", "frágil") is False
    assert glossary_generator._is_isolated_modifier(
        object(),
        "La política migratoria cambió.",
        "migratoria",
    ) is True


def test_enrich_article_publishes_without_glossary_when_all_items_are_rejected(
    glossary_generator,
    sample_a2_text_article,
    monkeypatch,
):
    monkeypatch.setattr(
        glossary_generator,
        "generate",
        MagicMock(
            return_value=[
                VocabularyItem(
                    term="drones",
                    english="drones",
                    explanation="aviones no tripulados",
                )
            ]
        ),
    )

    article = sample_a2_text_article.model_copy(
        update={"content": "Los drones volaron sobre la ciudad durante la noche."}
    )
    enriched = glossary_generator.enrich_article(article)

    assert enriched.vocabulary == []
    assert enriched.content == article.content
