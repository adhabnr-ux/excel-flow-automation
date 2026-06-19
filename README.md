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

## Native Scheduling (reduce live taps, safely)

What can and can't be scheduled, by platform (verified June 2026):

| Content | Native scheduling? | How it's handled here |
|---------|--------------------|-----------------------|
| LinkedIn Creator Shoutouts (personal feed) | ✅ Yes | Sunday digest → batch into LinkedIn's scheduler |
| LinkedIn polls | ❌ No (scheduler excludes polls) | Live Telegram tap |
| LinkedIn posts **inside Groups** | ❌ No (no native scheduling, no API — manual only) | Live Telegram tap |
| Substack Notes | ⚠️ Native scheduling exists but caps at ~5 queued | Live Telegram tap (by choice — cap too low for 21/week) |

Shoutouts go to the personal feed first, then get a manual in-group follow-up —
the digest reminds you of that second step (groups can't be automated at all).

**Every Sunday at 10 AM MST**, `schedule-digest.yml` sends a Telegram digest of
the coming week's schedulable posts with exact times + copy-ready text. Sit down
once, paste each into LinkedIn's scheduler (New post → 🕒 clock → set time →
Schedule), and that category publishes itself all week.

Preview the digest anytime:
```bash
python3 schedule_digest.py content/week-2026-06-15.json --dry-run
```

**Mark any post schedulable:** add `"schedulable": true` to a post in the JSON
(or `false` to force live-tap). By default only LinkedIn Creator Shoutouts are
schedulable. If you ever run a LinkedIn "poll" as a plain text post to chase
comments, mark it `true` and it joins the Sunday digest.

**Group follow-up reminder:** shoutouts get a digest reminder to do their manual
in-group follow-up. Override with `"group_followup": "your custom note"` on a
post, or `"group_followup": false` to suppress it.

**Stop double-pinging:** once you trust the Sunday routine, set the workflow
env var `SKIP_SCHEDULABLE: "true"` in `deliver.yml`. Then natively-scheduled
posts are omitted from the live tap — only polls ping you. (Default is off, so
nothing is ever silently dropped until you opt in.)

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
| `schedule_digest.py` | Sunday digest of natively-schedulable posts |
| `schedule_helper.py` | Shared `is_schedulable()` logic |
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
| `schedule-digest.yml` | Sunday 10 AM MST | Batch-scheduling digest |

## Required Secrets

GitHub → Settings → Secrets and variables → Actions:

- `TELEGRAM_BOT_TOKEN` — bot token from @BotFather
- `TELEGRAM_CHAT_ID` — your personal Telegram chat ID (numeric)
