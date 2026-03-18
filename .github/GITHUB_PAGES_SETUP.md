# GitHub Pages Setup Guide

This guide walks you through enabling GitHub Pages for the AutoSpanishBlog / Spai site.

## Prerequisites

- Repository with Jekyll site in `output/` directory
- At least 20 articles generated in `output/_posts/`
- GitHub account with repository access

## Step-by-Step Setup

### 1. Navigate to Repository Settings

1. Go to https://github.com/aizlabs/spai
2. Click **Settings** tab (top right)
3. In the left sidebar, click **Pages**

### 2. Configure Source

Under "Build and deployment":

**Source:**
- Select **Deploy from a branch**

**Branch:**
- Branch: `main`
- Folder: `/output` (or `/` if Jekyll files are in root)
- Click **Save**

### 3. Configure Custom Domain (Optional)

If you have a custom domain:

1. In the "Custom domain" field, enter: `spaili.com`
2. Click **Save**
3. Wait for DNS check to complete
4. Check **Enforce HTTPS** (recommended)

#### DNS Configuration for Custom Domain

Add these records to your domain registrar:

**For apex domain (`spaili.com`):**
```
A Record: 185.199.108.153
A Record: 185.199.109.153
A Record: 185.199.110.153
A Record: 185.199.111.153
```

**For `www` subdomain:**
```
CNAME Record: www → aizlabs.github.io
```

### 4. Verify Deployment

1. After saving, GitHub will start building your site
2. Check **Actions** tab to see build progress
3. Build takes 2-5 minutes
4. Once complete, visit your site:
   - Default: GitHub Pages project URL
   - Custom: https://spaili.com

## Site URLs

### Default GitHub Pages URL
- **URL:** repository-specific GitHub Pages project URL
- **Config:** only use a non-empty `baseurl` if you deploy as a project site under a subpath

### Custom Domain
- **URL:** https://spaili.com
- **Config:** keep `baseurl: ""` and `url: "https://spaili.com"` in `output/_config.yml`

## Troubleshooting

### Build Fails

**Check Actions Tab:**
1. Go to **Actions** tab
2. Click on failed workflow
3. Read error logs

**Common Issues:**
- Missing Gemfile or dependencies
- Invalid Jekyll configuration
- Syntax errors in layouts

**Solution:**
- Fix errors in `output/` directory
- Commit and push changes
- Rebuild will trigger automatically

### 404 Errors

**Baseurl Mismatch:**
- If using `/spai` subdirectory, ensure `baseurl: "/spai"` in `_config.yml`
- If using custom domain, ensure `baseurl: ""` (empty)

### CSS/JS Not Loading

**Asset Paths:**
- Ensure assets use `{{ '/assets/css/custom.css' | relative_url }}`
- Not absolute paths like `/assets/css/custom.css`

### Site Not Updating

**Cache:**
- Wait 5 minutes for CDN cache to clear
- Hard refresh browser: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Check **Actions** tab to confirm new build completed

## GitHub Pages Jekyll Build

GitHub Pages uses specific Jekyll versions and plugins:

### Allowed Plugins (Automatic)
- jekyll-sitemap
- jekyll-feed
- jekyll-seo-tag
- jekyll-paginate
- jemoji
- jekyll-mentions
- jekyll-redirect-from
- jekyll-avatar
- jekyll-remote-theme

### Using Minimal Mistakes Theme

Add to `_config.yml`:
```yaml
remote_theme: mmistakes/minimal-mistakes
```

Or use gem-based theme:
```yaml
theme: minimal-mistakes-jekyll
```

## Build Process

When you push to `main` branch:

1. GitHub detects changes in `output/` directory
2. Triggers Jekyll build
3. Compiles Markdown → HTML
4. Generates static site
5. Deploys to GitHub Pages CDN
6. Site live in 2-5 minutes

## Monitoring

### Check Build Status

**Via Web:**
- Go to **Actions** tab
- See "pages build and deployment" workflows
- Green checkmark = success
- Red X = failed

**Via Badge:**
Add to README.md:
```markdown
![GitHub Pages](https://github.com/aizlabs/spai/actions/workflows/pages/pages-build-deployment/badge.svg)
```

### Analytics Setup (Future)

Once site is live, set up:

1. **Google Analytics:**
   - Create GA4 property
   - Add tracking ID to `_config.yml`

2. **Google Search Console:**
   - Verify ownership
   - Submit sitemap: `https://your-site.com/sitemap.xml`

3. **Plausible (Privacy-friendly alternative):**
   - Sign up at https://plausible.io
   - Add script tag to `_includes/head/custom.html`

## Performance

### CDN
- GitHub Pages uses Fastly CDN
- Global edge caching
- HTTPS included free

### Optimization
- Minify CSS/JS (Jekyll handles this)
- Optimize images (use WebP)
- Lazy load images

## Limits

### GitHub Pages Limits
- **Bandwidth:** 100 GB/month (soft limit)
- **Builds:** 10/hour
- **Site size:** 1 GB
- **File size:** 100 MB per file

**Current usage:** ~2-3 MB for 360 articles

### Cost
- **$0** - Completely free!

## Security

### HTTPS
- Automatic with GitHub Pages
- Free SSL certificate via Let's Encrypt
- Force HTTPS: Check box in settings

### Branch Protection
Protect `main` branch:
1. Settings → Branches → Add rule
2. Branch name pattern: `main`
3. Enable:
   - Require pull request reviews
   - Require status checks

## Support

**GitHub Pages Docs:** https://docs.github.com/pages
**Jekyll Docs:** https://jekyllrb.com/docs/
**Minimal Mistakes Docs:** https://mmistakes.github.io/minimal-mistakes/docs/quick-start-guide/

**Issues:** https://github.com/aizlabs/spai/issues
