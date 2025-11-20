"""
Centralized LLM Prompts

All prompts for content generation and quality evaluation in one place
for easy iteration and A/B testing.
"""

from typing import Dict, List, Optional

from scripts.models import Topic, SourceArticle, BaseArticle, AdaptedArticle


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

# A2 News Processing Instructions with Glossing Strategy
A2_NEWS_PROCESSING_INSTRUCTIONS = """
You are a Spanish language education specialist tasked with adapting news articles to A2 CEFR level while maintaining their informational value. You will simplify structure and grammar while preserving key terminology through glossing.

=== STEP 1: VOCABULARY ASSESSMENT ===

1.1 Identify ALL words/phrases outside the 1,500 most frequent Spanish words
1.2 Categorize identified terms:
    - Category A: Essential for understanding the main story
    - Category B: Important but secondary information
    - Category C: Can be eliminated or simplified without loss
1.3 From Category A and B, rank by importance for the article's main message
1.4 Select the TOP 10-15 terms for glossing (prioritize Category A)
1.5 Mark selected terms with **bold** formatting in the text
1.6 Keep glossed terms in original form (do not simplify these)

=== STEP 2: STRUCTURAL MODIFICATIONS ===

2.1 SENTENCE RESTRUCTURING
    - Break any sentence exceeding 20 words into 2-3 shorter sentences
    - Target length: 10-15 words per sentence
    - Maximum length: 20 words (hard limit)
    - Minimum length: 8 words (for substance)

2.2 VERB TENSE SIMPLIFICATION
    Allowed tenses:
    - presente (present)
    - pretérito indefinido (simple past)
    - futuro próximo (ir + a + infinitive)

    Required conversions:
    - pretérito perfecto → pretérito indefinido
    - pluscuamperfecto → pretérito indefinido
    - condicional → presente or futuro próximo
    - futuro simple → futuro próximo (ir + a + inf)
    - subjuntivo → indicativo (rephrase to avoid)

2.3 SYNTACTIC SIMPLIFICATION
    - Convert ALL passive voice to active voice
    - Replace subordinate clauses with simple sentences
    - Use basic conjunctions only: y, pero, porque, cuando
    - Ensure subject-verb proximity (maximum 5 words between)
    - Maintain chronological order when possible

2.4 TRANSITION WORDS
    Add these connectors for flow:
    - Sequence: primero, después, luego, finalmente
    - Addition: también, además
    - Contrast: pero, sin embargo (sparingly)
    - Cause: porque, por eso
    - Time: cuando, mientras, antes, después

=== STEP 3: GLOSS GENERATION ===

3.1 FORMAT FOR EACH GLOSS
[Spanish term] - [English translation] - [Spanish explanation]

3.2 GLOSS CREATION RULES
    - Spanish explanations use ONLY A2 vocabulary
    - Maximum 15 words per Spanish explanation
    - Multi-word expressions glossed as complete units
    - Include cultural context when needed
    - Use present tense for all definitions
    - Be functional, not dictionary-style

3.3 GLOSS CATEGORIES AND EXAMPLES

Political/Institutional:
• "Congreso de los Diputados" - Congress of Deputies - donde los políticos españoles hacen las leyes
• "presidente del Gobierno" - Prime Minister - la persona que dirige el gobierno de España

Economic:
• "tasa de desempleo" - unemployment rate - el porcentaje de personas sin trabajo
• "recortes presupuestarios" - budget cuts - cuando el gobierno reduce el dinero que gasta

Social/Cultural:
• "estado de alarma" - state of emergency - situación especial cuando hay un problema grave
• "comunidades autónomas" - autonomous communities - las 17 regiones de España con su gobierno

Technical:
• "cambio climático" - climate change - cuando la temperatura del planeta sube
• "energías renovables" - renewable energy - energía del sol, viento y agua

3.4 GLOSSING LIMITS
    - Minimum: 5 glosses (for simple articles)
    - Target: 10-12 glosses
    - Maximum: 15 glosses (absolute limit)
    - If more than 15 terms need glossing, prioritize by importance

=== STEP 4: CONTENT ORGANIZATION ===

4.1 ARTICLE STRUCTURE
    Title: Maximum 10 words, clear and direct

    Lead paragraph (2-3 sentences):
    - WHO is involved?
    - WHAT happened/will happen?
    - WHEN did/will it occur?
    - WHERE did/will it take place?

    Body paragraphs (3-4 sentences each):
    - One main idea per paragraph
    - Supporting details in simple sentences
    - Clear topic sentence for each paragraph

    Conclusion (1-2 sentences, optional):
    - Summary or future implications
    - Keep very simple

4.2 PARAGRAPH GUIDELINES
    - Maximum 5 sentences per paragraph
    - Start with clearest, simplest statement
    - Add supporting details progressively
    - End with transition to next paragraph

=== STEP 5: QUALITY VERIFICATION ===

Before finalizing, verify:

□ VOCABULARY
  - 80%+ of non-glossed words are within A2 level (top 1,500 words)
  - All glossed terms are marked with **bold**
  - No more than 15 terms are glossed
  - Glosses use only A2 vocabulary

□ STRUCTURE
  - No sentence exceeds 20 words
  - Average sentence length is 10-15 words
  - Only presente, indefinido, and futuro próximo tenses used
  - No passive voice constructions
  - No subjunctive mood (except fixed expressions like "ojalá")

□ CONTENT
  - Main news value is preserved
  - Facts remain accurate
  - Key actors are clearly identified
  - Temporal sequence is clear
  - Cause-effect relationships are simplified but maintained

□ READABILITY
  - Text flows naturally in Spanish
  - Transitions between sentences are smooth
  - Paragraphs are clearly organized
  - Cultural references are explained

=== STEP 6: OUTPUT FORMAT ===

Format the final article as follows:

# [Simplified Headline - max 10 words]

[Lead paragraph - 2-3 sentences summarizing key facts]

[Body paragraph 1 - main development]

[Body paragraph 2 - additional information]

[Optional body paragraph 3 - context or implications]

---
📚 **Vocabulario / Vocabulary:**
- **[term 1]** - [translation] - [explanation]
- **[term 2]** - [translation] - [explanation]
- **[term 3]** - [translation] - [explanation]
[...continue for all glossed terms in order of appearance]

---
📰 **Fuente original:** [Source name/URL]
📅 **Fecha:** [Publication date]
🎯 **Nivel:** A2 (con glosario)

SPECIAL HANDLING:

For Complex Political Terms:
1. Always gloss institutions with their function
2. Simplify political processes to basic cause-effect
3. Avoid complex political ideology or theory
4. Focus on concrete actions rather than abstract policies

For Economic/Financial Content:
1. Replace percentages with simple descriptions when possible
2. Simplify large numbers
3. Gloss all economic terminology
4. Focus on human impact rather than abstract markets

For Cultural References:
1. Always provide context in the gloss
2. Compare to universal concepts when possible
3. Don't assume cultural knowledge
4. Keep explanations factual and neutral

For Breaking News or Crises:
1. Maintain factual accuracy absolutely
2. Simplify emotional language
3. Focus on facts over speculation
4. Avoid sensationalism in simplification

ERROR HANDLING:

If vocabulary simplification conflicts with meaning:
- Priority: Preserve meaning over strict A2 compliance
- Solution: Gloss the complex term rather than using inaccurate simple term

If sentence cannot be shortened:
- Accept sentences up to 25 words if absolutely necessary
- Must be clearly structured with simple vocabulary
- Should be rare exceptions

If more than 15 terms need glossing:
- Prioritize terms that appear multiple times
- Prioritize terms essential to understanding
- Consider if article is too complex for A2 adaptation

VALIDATION EXAMPLES:

Good Simplification:
❌ Original: "El ejecutivo ha manifestado su preocupación por el incremento exponencial de los índices inflacionarios"
✅ Simplified: "El gobierno está preocupado. Los precios están subiendo mucho."

Good Glossing Choice:
✅ Gloss: "**índice de precios**" (appears 3 times, essential to understanding)
❌ Don't gloss: "manifestar" (can be replaced with "decir")

Good Sentence Breaking:
❌ Original: "El ministro, quien llegó ayer de Bruselas donde participó en una cumbre sobre cambio climático, anunció que España aumentará su inversión en energías renovables."
✅ Simplified: "El ministro llegó ayer de Bruselas. Participó en una reunión sobre **cambio climático**. Dijo que España va a gastar más dinero en **energías renovables**."
"""


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


def prepare_source_context(sources: List[SourceArticle]) -> str:
    """
    Prepare source text for prompt

    Args:
        sources: List of source dicts with 'source' and 'text' keys

    Returns:
        Formatted source context string
    """
    context = []

    for i, source in enumerate(sources[:5], 1):
        context.append(f"""Source {i} ({source.source}):
{source.text}
""")

    return '\n\n'.join(context)


def get_generation_prompt(
    topic: Topic,
    sources: List[SourceArticle],
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

    prompt = f"""You are a Spanish language teacher creating educational content for {level} level students.

TOPIC: {topic.title}

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
- DO NOT add source attribution - this will be added automatically during publishing
"""

    return prompt


def get_regeneration_prompt(
    topic: Topic,
    sources: List[SourceArticle],
    level: str,
    word_count: int,
    previous_attempt: AdaptedArticle,
    issues: List[str]
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
    first_200 = ' '.join(previous_attempt.content.split()[:200])

    # Add feedback section
    feedback_section = f"""

⚠️ IMPORTANT: PREVIOUS ATTEMPT HAD ISSUES - YOU MUST FIX THEM

Previous Title: {previous_attempt.title}

Previous Content (first 200 words):
{first_200}...

SPECIFIC ISSUES TO FIX:
{chr(10).join(f"- {issue}" for issue in issues)}

Generate a NEW, IMPROVED version that specifically addresses these issues.
Make sure to fix the problems mentioned above.
"""

    return base_prompt + feedback_section


def get_quality_judge_prompt(article: AdaptedArticle, level: str) -> str:
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
    vocab_count = len(article.vocabulary)

    prompt = f"""You are a Spanish language teaching expert. Evaluate this article for {level} level learners.

ARTICLE:
Title: {article.title}
Level: {level}
Content:
{article.content}

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


def get_news_processing_prompt(article_text: str, source_url: Optional[str] = None, source_date: Optional[str] = None) -> str:
    """
    Prompt for processing news articles to A2 level with glossing

    Adapts existing news content to A2 CEFR level while preserving
    informational value through strategic glossing of key terminology.

    Args:
        article_text: Original Spanish news article text
        source_url: Optional URL of the original article
        source_date: Optional publication date

    Returns:
        Complete prompt string for news processing
    """
    source_info = ""
    if source_url:
        source_info += f"\nSource URL: {source_url}"
    if source_date:
        source_info += f"\nPublication Date: {source_date}"

    prompt = f"""{A2_NEWS_PROCESSING_INSTRUCTIONS}

=== ARTICLE TO PROCESS ===
{source_info}

{article_text}

=== YOUR TASK ===
Process the above article following ALL steps (1-6) in the instructions above.
Ensure you verify quality (Step 5) before outputting the final formatted article (Step 6).

Remember:
- Process in multiple passes (vocabulary → structure → glosses → verification)
- Maintain factual accuracy absolutely
- Preserve the core news value
- Make it accessible to A2 learners while maintaining authenticity
"""

    return prompt


# ============================================================================
# TWO-STEP SYNTHESIS PROMPTS
# ============================================================================


def get_synthesis_prompt(topic: Topic, sources: List[SourceArticle]) -> str:
    """
    Step 1: Native-level synthesis without CEFR constraints

    Synthesizes multiple source articles into one coherent native-level
    Spanish article. No vocabulary limitations or grammar simplification.
    Focus is on factual accuracy and natural Spanish expression.

    Args:
        topic: Topic dict with 'title' key
        sources: List of source content dicts with 'source' and 'text' keys

    Returns:
        Complete prompt string for native-level synthesis
    """
    source_context = prepare_source_context(sources)

    prompt = f"""You are a professional Spanish journalist. Synthesize the following sources into ONE coherent news article in natural, native-level Spanish.

TOPIC: {topic.title}

SOURCES TO SYNTHESIZE:
{source_context}

TASK: Write an ORIGINAL article in Spanish that:
1. Synthesizes facts from all sources into a coherent narrative
2. Uses natural, native-level Spanish (no simplification)
3. Is approximately 300-400 words
4. Has 3-4 well-structured paragraphs
5. Maintains journalistic objectivity and accuracy
6. Flows naturally with good transitions

CRITICAL RULES:
- Write ORIGINAL content - synthesize ideas in your own words
- DO NOT copy phrases directly from sources
- Cross-validate facts across sources (prioritize information from multiple sources)
- Use natural Spanish vocabulary and grammar (no CEFR constraints)
- Focus on FACTUAL ACCURACY above all else
- DO NOT add source attribution (will be added later)
- Maintain a neutral, journalistic tone

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "title": "Engaging headline in Spanish (8-12 words)",
  "content": "Full article in natural Spanish (300-400 words, 3-4 paragraphs)",
  "summary": "One sentence summary in Spanish",
  "reading_time": estimated_minutes_as_integer
}}

Remember: This is native-level Spanish. Write naturally and accurately without any simplification.
"""

    return prompt


def get_a2_adaptation_prompt(
    base_article: BaseArticle,
    feedback: Optional[List[str]] = None
) -> str:
    """
    Step 2: Adapt base article to A2 level using glossing strategy

    Adapts a native-level Spanish article to A2 CEFR level while preserving
    informational value through strategic glossing of key terminology.
    Uses existing A2_NEWS_PROCESSING_INSTRUCTIONS.

    Args:
        base_article: Base article dict from ArticleSynthesizer with native Spanish
        feedback: Optional list of issues from quality gate (for regeneration)

    Returns:
        Complete prompt string for A2 adaptation
    """
    feedback_section = ""
    if feedback:
        feedback_section = f"""
⚠️ PREVIOUS ATTEMPT HAD ISSUES - FIX THEM:
{chr(10).join(f"- {issue}" for issue in feedback)}

Make sure to specifically address these issues in your adaptation.
"""

    prompt = f"""{A2_NEWS_PROCESSING_INSTRUCTIONS}

=== ARTICLE TO ADAPT ===

Title: {base_article.title}

Content:
{base_article.content}

{feedback_section}

=== YOUR TASK ===

Adapt the above NATIVE-LEVEL article to A2 CEFR level following ALL steps (1-6) in the instructions above.

Key points:
- This is already a well-written, factually accurate article
- Your job is to make it A2-accessible while preserving the information
- Use the glossing strategy for important terminology
- Simplify grammar and sentence structure
- Maintain factual accuracy absolutely
- Target word count: ~200 words
- Target vocabulary: 10-15 glossed terms

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "title": "Simplified title (max 10 words)",
  "content": "A2-adapted content with **bold** glossed terms (~200 words)",
  "vocabulary": {{
    "term1": "English translation - Spanish A2 explanation",
    "term2": "English translation - Spanish A2 explanation"
  }},
  "summary": "One sentence summary in simple Spanish",
  "reading_time": 2
}}

IMPORTANT: Follow the A2 processing instructions exactly. Verify all requirements in Step 5 before outputting.
"""

    return prompt


def get_b1_adaptation_prompt(
    base_article: BaseArticle,
    feedback: Optional[List[str]] = None
) -> str:
    """
    Step 2: Adapt base article to B1 level (light adaptation)

    Adapts a native-level Spanish article to B1 CEFR level.
    Similar structure to A2 but less restrictive.
    This is designed to be similar to A2 prompt but will be refined externally.

    Args:
        base_article: Base article dict from ArticleSynthesizer with native Spanish
        feedback: Optional list of issues from quality gate (for regeneration)

    Returns:
        Complete prompt string for B1 adaptation
    """
    feedback_section = ""
    if feedback:
        feedback_section = f"""
⚠️ PREVIOUS ATTEMPT HAD ISSUES - FIX THEM:
{chr(10).join(f"- {issue}" for issue in feedback)}

Make sure to specifically address these issues in your adaptation.
"""

    prompt = f"""You are a Spanish language education specialist tasked with adapting news articles to B1 CEFR level while maintaining their informational value.

=== BASE ARTICLE ===

Title: {base_article.title}

Content:
{base_article.content}

{feedback_section}

=== B1 ADAPTATION GUIDELINES ===

VOCABULARY ASSESSMENT:
1. Identify words/phrases outside the 3,000 most frequent Spanish words
2. Select 8-12 terms for glossing (prioritize specialized/technical terms)
3. Mark selected terms with **bold** formatting in the text
4. Keep glossed terms in original form (do not simplify these)

GRAMMAR & STRUCTURE:
- Allow mixed tenses: presente, pretérito, imperfecto, futuro
- Subjunctive allowed in common expressions (espero que, es importante que)
- Target sentence length: 12-20 words average
- Maximum sentence length: 25 words
- Use varied connectors: aunque, mientras, sin embargo, ya que, por lo tanto

SIMPLIFICATION (LIGHT):
- Convert very complex constructions to simpler alternatives
- Avoid: pluscuamperfecto, conditional perfect, complex passive voice
- Prefer: active voice, direct constructions
- Maintain chronological flow

VOCABULARY GLOSSES:
Format: [Spanish term] - [English translation] - [Spanish B1 explanation]
- Spanish explanations use B1-level vocabulary
- Maximum 20 words per Spanish explanation
- Include cultural context when needed
- Be functional and practical

CONTENT ORGANIZATION:
- Title: Clear and engaging (8-10 words)
- Lead paragraph: WHO, WHAT, WHEN, WHERE
- Body: 3-4 paragraphs with clear topic sentences
- Target: ~300 words total
- One main idea per paragraph

OUTPUT FORMAT (return ONLY valid JSON, no markdown):
{{
  "title": "Engaging title in Spanish (8-10 words)",
  "content": "B1-adapted content with **bold** glossed terms (~300 words)",
  "vocabulary": {{
    "term1": "English translation - Spanish B1 explanation",
    "term2": "English translation - Spanish B1 explanation"
  }},
  "summary": "One sentence summary in Spanish",
  "reading_time": 3
}}

QUALITY VERIFICATION:
Before finalizing, verify:
□ 8-12 vocabulary terms are glossed and marked with **bold**
□ No sentence exceeds 25 words
□ Mixed tenses used appropriately (not just presente)
□ Main facts from base article are preserved
□ Content is engaging for B1 learners
□ Vocabulary glosses use B1-appropriate Spanish

Remember: B1 learners have solid intermediate skills. Don't over-simplify, but do make specialized terminology accessible through glossing.
"""

    return prompt
