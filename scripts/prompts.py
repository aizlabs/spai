"""
Centralized LLM Prompts

All prompts for content generation and quality evaluation in one place
for easy iteration and A/B testing.
"""

from typing import Dict, List, Optional


# Level-specific grammar rules
LEVEL_GENERATION_RULES = {
    'A2': """
- Use ONLY present tense (presente)
- Simple sentences (max 12 words per sentence)
- Vocabulary: Only the 1000 most common Spanish words
- NO subjunctive mood
- Short, clear sentences
""",
    'B1': """
- Mix tenses: present, preterite (pretérito), imperfect (imperfecto)
- Varied sentence length (8-18 words)
- Intermediate vocabulary
- You may use subjunctive in common expressions only
- Some complex sentences with subordinate clauses
"""
}

LEVEL_EVALUATION_CRITERIA = {
    'A2': """
A2 Level Grammar Expectations:
- Present tense (presente) should be primary
- Simple past (pretérito) for completed actions only
- NO subjunctive mood
- Simple sentence structures
- Basic connectors (y, pero, porque, cuando)
""",
    'B1': """
B1 Level Grammar Expectations:
- Mixed tenses: presente, pretérito, imperfecto
- Subjunctive in common expressions (espero que, es importante que)
- More complex sentences with subordinate clauses
- Varied connectors (aunque, mientras, sin embargo, ya que)
"""
}


def validate_level(level: str) -> None:
    """
    Validate that the level exists in both rule dictionaries

    Args:
        level: CEFR level to validate

    Raises:
        ValueError: If level is not supported
    """
    if level not in LEVEL_GENERATION_RULES:
        raise ValueError(
            f"Unsupported level '{level}'. "
            f"Supported levels: {', '.join(LEVEL_GENERATION_RULES.keys())}"
        )
    if level not in LEVEL_EVALUATION_CRITERIA:
        raise ValueError(
            f"Level '{level}' missing evaluation criteria. "
            f"Available criteria for: {', '.join(LEVEL_EVALUATION_CRITERIA.keys())}"
        )


def prepare_source_context(sources: List[Dict]) -> str:
    """
    Prepare source text for prompt

    Args:
        sources: List of source dicts with 'source' and 'text' keys

    Returns:
        Formatted source context string
    """
    context = []

    for i, source in enumerate(sources[:5], 1):
        context.append(f"""Source {i} ({source['source']}):
{source['text']}
""")

    return '\n\n'.join(context)


def get_generation_prompt(
    topic: Dict,
    sources: List[Dict],
    level: str,
    word_count: int
) -> str:
    """
    Prompt for initial article generation

    Generates an original Spanish article by synthesizing multiple sources.
    Uses level-specific grammar rules and vocabulary constraints.

    Args:
        topic: Topic dict with 'title' key
        sources: List of source content dicts
        level: CEFR level ('A2' or 'B1')
        word_count: Target word count (200 for A2, 300 for B1)

    Returns:
        Complete prompt string for LLM

    Raises:
        ValueError: If level is not supported
    """
    validate_level(level)
    source_context = prepare_source_context(sources)
    source_names = [s['source'] for s in sources[:3]]

    prompt = f"""You are a Spanish language teacher creating educational content for {level} level students.

TOPIC: {topic['title']}

REFERENCE SOURCES (synthesize information, DO NOT copy text):
{source_context}

TASK: Create an ORIGINAL article in Spanish that:
1. Synthesizes information from the sources above in your own words
2. Is appropriate for {level} Spanish learners
3. Is approximately {word_count} words long
4. Has 3 clear paragraphs with good flow
5. Includes cultural context relevant to Spanish speakers
6. Is engaging and educational

LEVEL REQUIREMENTS for {level}:
{LEVEL_GENERATION_RULES[level]}

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "title": "Engaging title in Spanish (5-8 words)",
  "content": "Full article text in Spanish (~{word_count} words, 3 paragraphs)",
  "vocabulary": {{
    "word1": "English translation",
    "word2": "English translation"
  }},
  "summary": "One sentence summary in Spanish",
  "reading_time": estimated_minutes_as_integer
}}

CRITICAL RULES:
- Write ORIGINAL content - synthesize ideas but use your own words
- DO NOT copy phrases from the sources
- This is educational fair use - transform the information

Attribution line to add at end of content:
"Fuentes: {', '.join(source_names)}"
"""

    return prompt


def get_regeneration_prompt(
    topic: Dict,
    sources: List[Dict],
    level: str,
    word_count: int,
    feedback: Dict
) -> str:
    """
    Prompt for article regeneration with feedback

    Used when quality check fails. Includes previous attempt and specific
    issues that need to be fixed.

    Args:
        topic: Topic dict with 'title' key
        sources: List of source content dicts
        level: CEFR level ('A2' or 'B1')
        word_count: Target word count
        feedback: Dict with 'previous_title', 'previous_content', 'issues'

    Returns:
        Complete prompt string with feedback section
    """
    # Get base prompt
    base_prompt = get_generation_prompt(topic, sources, level, word_count)

    # Truncate previous content to first 200 words for context
    first_200 = ' '.join(feedback['previous_content'].split()[:200])

    # Add feedback section
    feedback_section = f"""

⚠️ IMPORTANT: PREVIOUS ATTEMPT HAD ISSUES - YOU MUST FIX THEM

Previous Title: {feedback['previous_title']}

Previous Content (first 200 words):
{first_200}...

SPECIFIC ISSUES TO FIX:
{chr(10).join(f"- {issue}" for issue in feedback['issues'])}

Generate a NEW, IMPROVED version that specifically addresses these issues.
Make sure to fix the problems mentioned above.
"""

    return base_prompt + feedback_section


def get_quality_judge_prompt(article: Dict, level: str) -> str:
    """
    Prompt for quality evaluation

    LLM judge scores article on 4 criteria (0-10 total):
    - Grammar & Language (0-4)
    - Educational Value (0-3)
    - Content Quality (0-2)
    - Level Appropriateness (0-1)

    Args:
        article: Article dict with 'title', 'content', 'vocabulary'
        level: CEFR level ('A2' or 'B1')

    Returns:
        Complete prompt string for quality judge

    Raises:
        ValueError: If level is not supported
    """
    validate_level(level)
    vocab_count = len(article.get('vocabulary', {}))

    prompt = f"""You are a Spanish language teaching expert. Evaluate this article for {level} level learners.

ARTICLE:
Title: {article['title']}
Level: {level}
Content:
{article['content']}

Vocabulary provided: {vocab_count} words

EVALUATION CRITERIA (total 0-10 points):

1. Grammar & Language (0-4 points):
{LEVEL_EVALUATION_CRITERIA[level]}
- Are there any grammar errors?
- Is the grammar appropriate for {level}?

2. Educational Value (0-3 points):
- Is this interesting and useful for Spanish learners?
- Does it teach cultural concepts?
- Are the vocabulary words relevant and useful?

3. Content Quality (0-2 points):
- Is the information accurate and coherent?
- Is it well-structured (clear paragraphs)?
- Does it flow naturally?

4. Level Appropriateness (0-1 point):
- Is vocabulary suitable for {level}?
- Is sentence complexity appropriate?
- Would this engage {level} learners?

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "grammar_score": 0-4,
  "grammar_issues": ["specific issue 1", "specific issue 2"] or [],

  "educational_score": 0-3,
  "educational_notes": "brief comment",

  "content_score": 0-2,
  "content_issues": ["issue1"] or [],

  "level_score": 0-1,

  "total_score": sum_of_all_scores,

  "issues": ["All specific issues that need fixing"],
  "strengths": ["What the article does well"],

  "recommendation": "PASS or FAIL with reason"
}}

BE STRICT. A score of 7.5+ means genuinely good educational content.
Lower scores should identify specific, actionable issues to fix.
"""

    return prompt
