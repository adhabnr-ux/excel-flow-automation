# Excel Flow Automation — Setup

The automation runs on **GitHub Actions**, so it works with your computer off
and you away.

## Already built

- `deliver.py` — the delivery script
- `.github/workflows/deliver.yml` — the 3 daily schedules + a manual trigger
- `content/week-2026-05-18.json` — all 42 posts for this week, verbatim
- `carousels/` — the 3 carousel PDFs, pre-rendered
- Repo created and pushed.

## Your steps

### Step 1 — Add the 2 secrets
The workflow needs your CallMeBot credentials. Two ways:

**On github.com:** repo → Settings → Secrets and variables → Actions → New
repository secret. Add two:
- Name `CALLMEBOT_PHONE` — value: your CallMeBot phone number
- Name `CALLMEBOT_APIKEY` — value: your CallMeBot API key

**Or from your terminal** (value is typed in, never shown):
```
gh secret set CALLMEBOT_PHONE
gh secret set CALLMEBOT_APIKEY
```

### Step 2 — Test run
On github.com: **Actions** tab → **Excel Flow Delivery** → **Run workflow** →
pick a window (e.g. Morning) → **Run workflow**. Confirm a WhatsApp message
arrives. The run log also prints the full batch report.

### Step 3 — Live
The 3 daily schedules now run on their own. Nothing else to do.

## What I still need from you

1. **Substack edition URLs** for editions #18, #23, #25, #26, #27, #28, #29 —
   to replace the `[Substack URL for Edition #X]` placeholders. Until then the
   QA step flags them in WhatsApp.
2. **Your LinkedIn display name + handle** — for the `[YOUR_HANDLE]` footer on
   the carousel slides.

Send those in chat; I update the content, re-render the carousels, and push.

## Weekly, going forward

Paste next week's content to me in chat. I rewrite `content/`, re-render
`carousels/`, commit, and push. You do nothing — the workflow never changes.

## Notes

- GitHub Actions cron can run a few minutes late under load. The schedules fire
  60–90 min before the earliest post, so a delay never matters.
- GitHub disables scheduled workflows after 60 days of no repo activity. The
  weekly content commits keep it alive.
- **Known issue:** several LinkedIn poll options exceed LinkedIn's 30-character
  limit per option. The QA step flags each one in the WhatsApp message — trim
  before posting, or tell me and I'll trim them in the content file.
- **Honest limits:** post content is delivered 100% verbatim. Delivery rides on
  CallMeBot (a free relay) — best-effort; if a message misfires, the full batch
  is in the GitHub Actions run log, and a failed run emails you.
