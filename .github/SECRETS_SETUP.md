# GitHub Secrets Setup

To enable automated article generation, you need to configure the following secrets in your GitHub repository.

## Required Secrets

### 1. LLM API Keys

Go to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### OPENAI_API_KEY
- **Name:** `OPENAI_API_KEY`
- **Value:** Your OpenAI API key (starts with `sk-proj-...`)
- **Used for:** Article generation (GPT-4o) and quality checking (GPT-4o-mini)

#### ANTHROPIC_API_KEY (Optional)
- **Name:** `ANTHROPIC_API_KEY`
- **Value:** Your Anthropic API key (starts with `sk-ant-...`)
- **Used for:** Fallback LLM provider if needed

### 2. Email Notifications (Optional)

When **all three** of `ALERT_EMAIL`, `EMAIL_USERNAME`, and `EMAIL_PASSWORD` are set, the **pipeline's AlertManager** sends
failure emails (not only the workflow step). The workflow's "Notify on failure" step is then skipped to avoid duplicate
notifications. When alerts are enabled, the pipeline also sends a short success email after a run that published at least
one article (summary of count, levels, attempts, and titles). If you don't set these up, the workflow will still run but
won't send email notifications.

#### EMAIL_USERNAME
- **Name:** `EMAIL_USERNAME`
- **Value:** Your Gmail address (e.g., `your.email@gmail.com`)

#### EMAIL_PASSWORD
- **Name:** `EMAIL_PASSWORD`
- **Value:** Gmail App Password (NOT your regular password)
- **How to get:**
  1. Go to https://myaccount.google.com/apppasswords
  2. Create a new app password for "Mail"
  3. Copy the 16-character password
  4. Use this as the secret value

#### ALERT_EMAIL
- **Name:** `ALERT_EMAIL`
- **Value:** Email address to receive alerts (can be same as EMAIL_USERNAME)

#### Optional: ALERT_SMTP_HOST, ALERT_SMTP_PORT, ALERT_SENDER
- **ALERT_SMTP_HOST:** SMTP host (default: `smtp.gmail.com`). Set for SendGrid, Mailgun, etc.
- **ALERT_SMTP_PORT:** SMTP port (default: `587`).
- **ALERT_SENDER:** From address for alert emails (e.g. `AutoSpanishBot <noreply@example.com>`). Used by the pipeline when set.

### 3. Telegram Notifications (Optional)

When **both** `ALERT_TELEGRAM_BOT_TOKEN` and `ALERT_TELEGRAM_CHAT_ID` are set, the **pipeline's AlertManager** sends the same
success and failure alerts to Telegram. These secrets also auto-enable pipeline alert delivery, unless `ALERTS_ENABLED=false`
is explicitly set.

#### ALERT_TELEGRAM_BOT_TOKEN
- **Name:** `ALERT_TELEGRAM_BOT_TOKEN`
- **Value:** Bot token from BotFather (for example `123456:ABC...`)

#### ALERT_TELEGRAM_CHAT_ID
- **Name:** `ALERT_TELEGRAM_CHAT_ID`
- **Value:** Telegram chat ID for your private chat, group, or channel (for example `123456789` or `-1001234567890`)

## Verification

After setting up secrets, you can verify they're configured by:

1. Going to **Actions** tab
2. Selecting **Generate Spanish Learning Articles** workflow
3. Clicking **Run workflow** (manual trigger)
4. Checking the workflow runs successfully

## Security Notes

- Never commit API keys to git
- Rotate API keys every 90 days
- Use separate API keys for production vs development
- Monitor API usage through provider dashboards

## Cost Monitoring

- OpenAI: https://platform.openai.com/usage
- Anthropic: https://console.anthropic.com/settings/usage

Expected monthly cost: ~$10-12 for 360 articles/month (12/day)
