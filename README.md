# Excel Flow Automation

Automated content delivery for the Excel Flow newsletter. Posts go from JSON content files to Telegram at scheduled times — LinkedIn and Substack posts delivered daily across three windows.

LinkedIn's API cannot create polls and Substack has no posting API, so true auto-posting is impossible. This is a **prep-and-deliver** system: it sends the exact post text to Telegram at the right time; you do the final publish tap (~20–30s per post).

## Delivery Windows (America/Phoenix, no DST)

| Window  | MST Time | UTC Cron  |
|---------|----------|-----------|
| Morning | 6:30 AM  | 13:30 UTC |
| Midday  | 11:00 AM | 18:00 UTC |
| Evening | 4:00 PM  | 23:00 UTC |

## Manual Re-delivery

If a window was missed (cron failed, or you need to re-deliver):
1. GitHub → Actions → **Excel Flow Delivery** → **Run workflow**
2. Select the window (Morning / Midday / Evening)
3. Run workflow

If sentinels are blocking: delete `delivered/YYYY-MM-DD-Window.txt`, commit, push, then trigger manually.

## Required Secrets

GitHub → Settings → Secrets and variables → Actions:

- `TELEGRAM_BOT_TOKEN` — bot token from @BotFather
- `TELEGRAM_CHAT_ID` — your personal Telegram chat ID (numeric)
