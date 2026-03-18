# Local Jekyll Development Guide

This guide explains how to preview the Jekyll site locally before deploying to GitHub Pages.

## Prerequisites

- Ruby 2.7+ (Jekyll requirement)
- Bundler gem

## Quick Start

### 1. Install Ruby and Bundler

**macOS:**
```bash
# Using Homebrew
brew install ruby

# Add Ruby to PATH (add to ~/.zshrc or ~/.bash_profile)
export PATH="/opt/homebrew/opt/ruby/bin:$PATH"

# Install Bundler
gem install bundler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ruby-full build-essential
gem install bundler
```

**Windows:**
- Download and install from [RubyInstaller](https://rubyinstaller.org/)
- Run `gem install bundler` in command prompt

### 2. Install Jekyll Dependencies

```bash
# Navigate to Jekyll directory
cd output/

# Install dependencies from Gemfile
bundle install
```

This will install:
- Jekyll
- Minimal Mistakes theme
- All required plugins

### 3. Serve Site Locally

```bash
# From output/ directory
bundle exec jekyll serve

# Or with live reload
bundle exec jekyll serve --livereload

# Or on a different port
bundle exec jekyll serve --port 4001
```

### 4. View in Browser

Open your browser to:
```
http://localhost:4000/
```

The current production config uses an empty `baseurl`, so local preview should normally be served from the root path.

## Configuration for Local Development

### Option 1: Temporary Override (Recommended)

Run with config override:
```bash
bundle exec jekyll serve --config _config.yml,_config_dev.yml
```

Create `output/_config_dev.yml`:
```yaml
# Local development overrides
baseurl: ""
url: "http://localhost:4000"
```

Then visit: `http://localhost:4000/`

### Option 2: Comment Out Baseurl

Temporarily edit `output/_config.yml`:
```yaml
# For local development, comment out baseurl:
# baseurl: "/spai"
baseurl: ""
```

**Remember to uncomment before pushing to GitHub!**

## Common Commands

```bash
# Basic serve
bundle exec jekyll serve

# With drafts
bundle exec jekyll serve --drafts

# With future posts
bundle exec jekyll serve --future

# Incremental build (faster)
bundle exec jekyll serve --incremental

# Clean and rebuild
bundle exec jekyll clean
bundle exec jekyll serve

# Build only (no server)
bundle exec jekyll build
```

## Directory Structure

```
output/
├── _config.yml          # Jekyll configuration
├── _layouts/            # Custom layouts
├── _pages/              # Static pages (about, contact, etc.)
├── _posts/              # Generated articles
├── assets/              # CSS, JS, images
├── _site/               # Generated site (gitignored)
└── Gemfile              # Ruby dependencies
```

## Troubleshooting

### Port Already in Use

```bash
# Kill existing Jekyll process
pkill -f jekyll

# Or use different port
bundle exec jekyll serve --port 4001
```

### Gem Installation Fails

```bash
# Update bundler
gem update bundler

# Clear cache and reinstall
bundle clean --force
bundle install
```

### Theme Not Loading

```bash
# Reinstall gems
bundle clean --force
rm Gemfile.lock
bundle install
```

### Changes Not Showing

```bash
# Hard refresh browser
# Mac: Cmd + Shift + R
# Windows: Ctrl + Shift + R

# Or clear Jekyll cache
bundle exec jekyll clean
bundle exec jekyll serve
```

### CSS Not Loading

Check baseurl in `_config.yml`:
- Local: `baseurl: ""`
- Production: `baseurl: ""`

## Live Reload

For automatic browser refresh on changes:

```bash
# Install livereload
gem install eventmachine --platform ruby

# Serve with livereload
bundle exec jekyll serve --livereload
```

Then visit `http://localhost:4000/` and edits will auto-refresh.

## Testing Articles

### View Existing Articles

```bash
# List all articles
ls _posts/

# View article in browser
# Navigate to http://localhost:4000/articles/[article-slug]/
```

### Test Article Format

Create test article in `_posts/`:
```markdown
---
title: "Test Article"
date: 2025-11-12
level: A2
topics: ["test", "example"]
sources: "Manual Test"
reading_time: 2
---

Test content here.

## Vocabulario

- **palabra** - word
- **ejemplo** - example
```

### Preview Before Generation

```bash
# Generate articles in local environment
ENVIRONMENT=local uv run spai-pipeline

# View in Jekyll
cd output/
bundle exec jekyll serve
```

## Production Preview

To preview exactly as it will appear on GitHub Pages:

```bash
# Use production config
JEKYLL_ENV=production bundle exec jekyll serve
```

This enables:
- Production optimizations
- Analytics (if configured)
- AdSense (if configured)

## Docker Alternative

If you prefer Docker (no Ruby installation needed):

```bash
# From project root
docker run --rm \
  --volume="$PWD/output:/srv/jekyll" \
  --publish 4000:4000 \
  jekyll/jekyll:4.2.2 \
  jekyll serve
```

Visit: `http://localhost:4000/`

## Makefile Helper (Optional)

Create `output/Makefile`:
```makefile
.PHONY: serve clean build

serve:
	bundle exec jekyll serve --livereload

serve-drafts:
	bundle exec jekyll serve --drafts --livereload

build:
	bundle exec jekyll build

clean:
	bundle exec jekyll clean
	rm -rf _site/

install:
	bundle install
```

Then run:
```bash
make serve      # Start local server
make clean      # Clean generated files
make build      # Build site
```

## Performance Tips

### Faster Builds

```bash
# Incremental builds (only rebuild changed files)
bundle exec jekyll serve --incremental

# Limit posts (during development)
bundle exec jekyll serve --limit_posts 10

# Disable plugins temporarily
bundle exec jekyll serve --disable-disk-cache
```

### Watch Specific Directories

```bash
# Only watch posts
bundle exec jekyll serve --watch _posts/
```

## Integration with Pipeline

### Full Local Workflow

```bash
# 1. Generate articles
cd /path/to/spai
ENVIRONMENT=local uv run spai-pipeline

# 2. Preview in Jekyll
cd output/
bundle exec jekyll serve

# 3. View in browser
open http://localhost:4000/

# 4. If satisfied, commit
cd ..
git add output/_posts/
git commit -m "Add new articles"
```

## Differences: Local vs GitHub Pages

| Feature | Local | GitHub Pages |
|---------|-------|--------------|
| Build time | Instant | 2-5 minutes |
| Plugins | All | Whitelist only |
| Custom gems | Allowed | Limited |
| Debugging | Full access | Limited logs |
| HTTPS | No | Yes (automatic) |

## Next Steps

Once satisfied with local preview:

1. **Commit changes:**
   ```bash
   git add output/
   git commit -m "Add Jekyll site and articles"
   ```

2. **Push to GitHub:**
   ```bash
   git push origin main
   ```

3. **Enable GitHub Pages:**
   - Follow [GitHub Pages Setup Guide](.github/GITHUB_PAGES_SETUP.md)

4. **View live site:**
   - https://spaili.com

## Support

**Jekyll Docs:** https://jekyllrb.com/docs/
**Minimal Mistakes Docs:** https://mmistakes.github.io/minimal-mistakes/
**GitHub Pages Docs:** https://docs.github.com/pages

**Issues:** https://github.com/aizlabs/spai/issues
