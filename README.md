# Excel Flow Automation

Automated content delivery for the Excel Flow newsletter. Posts go from JSON content files to Telegram at scheduled times — LinkedIn and Substack posts delivered daily across three windows.

LinkedIn's API cannot create polls and Substack has no posting API, so true auto-posting is impossible. This is a **prep-and-deliver** system: it sends the exact post text to Telegram at the right time; you do the final publish tap (~20–30s per post).

## Delivery Windows (America/Phoenix, no DST)

| Window  | MST Time | UTC Cron  |
|---------|----------|-----------|
| Morning | 6:30 AM  | 13:30 UTC |
| Midday  | 11:00 AM | 18:00 UTC |
| Evening | 4:00 PM  | 23:00 UTC |

## Weekly Workflow

### Step 1 — Scaffold next week's file
```bash
python3 scripts/new_week.py 2026-06-22
```
Creates `content/week-2026-06-22.json` with all 44 post slots pre-populated (correct dates, windows, IDs). Fill in the `content` and `first_comment` fields.

### Step 2 — Validate before pushing
```bash
python3 validate.py
```
Catches schema errors, wrong window/platform values, duplicate IDs, unresolved placeholders. Exit code 0 = clean.

### Step 3 — Preview what will be sent (optional)
```bash
python3 deliver.py Morning --dry-run
```
Prints every Telegram message that would be sent — no API calls made. Good for checking before a window fires.

### Step 4 — Commit and push
```bash
git add content/week-2026-06-22.json && git commit -m "Add week of June 22" && git push
```

## Adding a New Edition URL

When a new edition publishes:
```bash
python3 scripts/add_edition.py 32 https://rileystream.substack.com/p/your-slug
git add editions.json && git commit -m "add edition #32 URL" && git push
```

This auto-resolves any `[link]` or `[Edition #32 link]` placeholders at delivery time.

## Manual Re-delivery

If a window was missed (cron failed, or you need to re-deliver):
1. GitHub → Actions → **Excel Flow Delivery** → **Run workflow**
2. Select the window (Morning / Midday / Evening)
3. Run workflow

If sentinels are blocking: delete `delivered/YYYY-MM-DD-Window.txt`, commit, push, then trigger manually.

## Files

| File | Purpose |
|------|---------|
| `deliver.py` | Core delivery script — run by GitHub Actions |
| `validate.py` | Schema validator for content files |
| `editions.json` | Edition number → Substack URL registry |
| `metrics_reminder.py` | Sunday 9 PM Telegram metrics checklist |
| `scripts/new_week.py` | Scaffolds a new week content file |
| `scripts/add_edition.py` | Registers a new edition URL |
| `content/week-*.json` | Weekly post content (one file per week) |
| `delivered/` | Sentinel files — one per delivered window |

## Workflows

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `deliver.yml` | Schedule (3x/day) + manual + cron-job.org | Deliver posts |
| `validate.yml` | Push/PR to content files | Validate schema |
| `metrics-reminder.yml` | Sunday 9 PM MST | Weekly metrics checklist |

## Required Secrets

GitHub → Settings → Secrets and variables → Actions:

- `TELEGRAM_BOT_TOKEN` — bot token from @BotFather
- `TELEGRAM_CHAT_ID` — your personal Telegram chat ID (numeric)
