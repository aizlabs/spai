# AutoSpanishBlog - Phase 1 Development Guide

**Phase:** MVP Core
**Goal:** End-to-end pipeline working locally
**Stack:** Python 3.11 + uv

---

## Quick Start

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# One-command setup! (creates venv, installs all deps including SpaCy model)
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Create output directories
mkdir -p output/_posts logs

# Test topic discovery
uv run spai-discover
```

---

## Project Structure

```
spai/
├── scripts/              # Python modules
│   ├── test_discovery.py     # Test topic discovery
│   ├── test_fetcher.py       # Test content fetcher
│   ├── topic_discovery.py    # RSS + SpaCy NER
│   ├── content_fetcher.py    # Trafilatura scraping with parallel fetch
│   ├── config.py             # Config loading
│   ├── logger.py             # Logging setup
│   ├── diagnose_sources.py   # RSS diagnostic tool
│   ├── content_generator.py  # LLM article generation
│   ├── quality_gate.py       # LLM quality judge
│   ├── publisher.py          # Jekyll markdown output
│   ├── metrics.py            # Metrics collection
│   ├── alerts.py             # Alert system
│   └── main.py               # Pipeline orchestrator
│
├── config/
│   ├── base.yaml        # Base settings
│   ├── local.yaml       # Dev overrides
│   ├── production.yaml  # Prod overrides
│   └── sources.yaml     # RSS feed list (32 sources)
│
├── output/              # gitignored
│   ├── _posts/          # Generated articles
│   ├── logs/            # Production logs
│   └── metrics/         # Run metrics
│
├── logs/                # Local logs (gitignored)
├── pyproject.toml       # Python project config
├── mypy.ini             # mypy type checking configuration
├── .python-version      # Python version (3.11)
└── .env                 # Environment variables (gitignored)
```

---

## Key Files Overview

**Design Documents:**
- `DESING.md` - Complete system design (1587 lines)
- **Useful code examples in `example-code/` directory**

**Configuration:**
- `config/base.yaml` - Shared settings for discovery, ranking, and fetching
- `config/sources.yaml` - 22 Spanish RSS feeds + Wikipedia (100% working)
- `config/local.yaml` - Dev mode (colored logs, 2 articles/run)

**Components Implemented:**
- `scripts/topic_discovery.py` - Multi-source topic discovery with SpaCy NER
- `scripts/content_fetcher.py` - Article fetcher with Trafilatura and parallel processing
- `scripts/test_discovery.py` - Topic discovery test harness
- `scripts/test_fetcher.py` - Content fetcher test harness

---

## Commands

```bash
# Test topic discovery
uv run spai-discover

# Test content fetcher
uv run spai-fetch

# Run full pipeline
uv run spai-pipeline

# View logs in real-time
tail -f logs/local.log

# Check generated articles
ls output/_posts/

# Diagnose source issues
python scripts/diagnose_sources.py

# List configured sources
python -c "
from scripts.config import load_config
config = load_config('local')
for i, s in enumerate(config.sources_list, 1):
    print(f'{i:2}. {s[\"name\"]:25} ({s[\"type\"]})')
"

# Quick sanity check
python -c "
from scripts.config import load_config
from scripts.logger import setup_logger
from scripts.topic_discovery import TopicDiscoverer

config = load_config('local')
logger = setup_logger(config, 'test')
discoverer = TopicDiscoverer(config, logger)
topics = discoverer.discover(limit=3)
print(f'✓ Found {len(topics)} topics')
"
```

### Type Checking with mypy

The project uses **mypy** for static type checking. All code should pass mypy validation.

```bash
# Install dev dependencies (includes mypy)
uv sync --extra dev

# Run type checking
uv run mypy scripts/ --config-file mypy.ini

# Run with error codes for detailed output
uv run mypy scripts/ --config-file mypy.ini --show-error-codes
```

**Status:**
- ✅ mypy is configured in `mypy.ini`
- ✅ Currently **0 type errors** across all files
- ⚠️ **Manual invocation required** - not integrated into CI/pre-commit hooks yet
- 📝 Run before committing to catch type issues early

**Configuration:**
- Config file: `mypy.ini`
- Type stubs: `scripts/py.typed` marker file
- Settings: Moderate strictness (allows untyped defs, but checks typed code)

---

## Git Worktree Workflow

```bash
# Create worktrees for parallel dev
git worktree add ../spai-discovery feature/topic-discovery
git worktree add ../spai-fetcher feature/content-fetcher
git worktree add ../spai-generator feature/content-generator
git worktree add ../spai-quality feature/quality-gate

# Work in worktree
cd ../spai-discovery
# ... make changes ...
git commit -m "Implement discovery"

# Clean up
git worktree remove ../spai-discovery
```

---

## Development Tips

1. **Start small:** Test with 1 article first, then scale
2. **Test components in isolation:** Run test scripts directly
3. **Use worktrees:** Work on multiple components in parallel
5. **Check logs frequently:** `tail -f logs/local.log` during development
6. **Lower quality threshold for testing:** Set `min_score: 6.0` in `config/local.yaml`
7. **Track costs:** Watch token usage in logs
8. **Commit working states:** Commit after each component works
9. **Read example code:** All components have working implementations in `example-code/`
10. **Test sources first:** Ensure RSS feeds work before building full pipeline

---

## Configuration

**Config hierarchy:**
```
base.yaml → local.yaml → ENV vars → final config
```

**Key settings:**
- `quality_gate.min_score: 7.5`
- `quality_gate.max_attempts: 3`
- `generation.articles_per_run: 2` (local) / `4` (prod)
- `generation.target_word_count: {A2: 200, B1: 300}`
- `discovery.min_sources: 3` (cross-source validation)
- `ranking.cultural_bonus: 5` (for learner-friendly topics)

**Expected costs:**
- Per article: $0.031 (with regeneration)
- Phase 1 testing (50 articles): $1.50-2.00
- Daily production (12 articles): $0.37

---

## Success Criteria

**Functional:**
- ✅ Topic discovery finds 10+ topics from 30+ sources
- ✅ Each topic validated by 3+ different sources
- ✅ Articles in Spanish at correct CEFR levels
- ✅ Quality scores average 7.5+

**Performance:**
- ✅ Topic discovery: ~9 seconds (parallel fetching from 22 sources)
- ✅ Full pipeline: 8-12 minutes for 4 articles
- ✅ Cost per run: $0.10-0.20

**Quality:**
- ✅ 80%+ articles pass quality gate
- ✅ A2: simple present tense
- ✅ B1: mixed tenses, subjunctive
- ✅ No obvious copying from sources

---

## Troubleshooting

### SpaCy Model Error
```bash
# Error: [E050] Can't find model 'es_core_news_sm'
# Solution: The model is included in pyproject.toml, just run:
uv sync

# Verify installation
uv run python -c "import spacy; nlp = spacy.load('es_core_news_sm'); print('✓ Model loaded')"
```

### Virtual Environment Issues
```bash
# Recreate environment from scratch (fully reproducible)
rm -rf .venv
uv sync

# This installs everything including the SpaCy model thanks to uv.lock
```

### API Key Not Found
```bash
# Check if key is set
echo $ANTHROPIC_API_KEY

# If empty, add to .env file
cp .env.example .env
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...
```

### Import Errors
```bash
# Make sure you're in the project root
pwd  # Should be .../spai/spai

# Check Python location (should be system Python, not venv)
which python

# Verify packages installed
uv pip list | grep -E "spacy|anthropic|feedparser"
```

### Test Fails
```bash
# Run with verbose output
python scripts/test_discovery.py 2>&1 | tee test_output.log

# Check specific source
python scripts/diagnose_sources.py

# View detailed logs
tail -100 logs/local.log
```

### Type Checking Issues
```bash
# Run mypy to see all type errors
uv run mypy scripts/ --config-file mypy.ini --show-error-codes

# Common fixes:
# - Add type hints to function parameters and return types
# - Use Pydantic models instead of dicts
# - Add type: ignore comments only when necessary (with specific error codes)
# - Use Union types for variables that can be multiple types (e.g., Union[Anthropic, OpenAI])
```

---
