# Excel Flow — Posting Automation

Delivers Excel Flow's daily LinkedIn + Substack posts to WhatsApp, ready to
paste, at the right time. Runs entirely on **GitHub Actions** — no computer
required.

## Why it works this way

LinkedIn's API cannot create polls and Substack has no posting API, so true
auto-posting is impossible. This is a **prep-and-deliver** system: it assembles
every post perfectly and texts it to you; you do the final publish tap
(~20–30s per post).

## How it runs

GitHub Actions runs `deliver.py` three times a day (cron is in UTC;
America/Phoenix is UTC-7 with no daylight saving):

| Window  | Cron (UTC)      | Local (MST) |
|---------|-----------------|-------------|
| Morning | `30 13 * * *`   | 06:30       |
| Midday  | `0 18 * * *`    | 11:00       |
| Evening | `0 23 * * *`    | 16:00       |

Each run reads `content/week-*.json`, takes today's posts for that window,
QA-checks them, and sends each as its own WhatsApp message via CallMeBot.
Carousel posts deliver a link to a pre-rendered PDF in `carousels/`.

## Files

- `deliver.py` — the delivery script (Python standard library only)
- `.github/workflows/deliver.yml` — the 3 cron schedules + manual trigger
- `content/week-*.json` — the posts, one file per week
- `carousels/*.pdf` — pre-rendered carousel PDFs
- `carousel-renderer.py` — regenerates carousel PDFs from a spec (local tool)
- `SETUP.md` — one-time setup
- `DESIGN.md` — full design spec

## Weekly

Hand next week's content to Claude in chat. Claude rewrites `content/`,
re-renders `carousels/`, commits, and pushes. The workflow and script never
change.

## Secrets

Set in the repo: Settings → Secrets and variables → Actions.

- `CALLMEBOT_PHONE` — your CallMeBot phone number
- `CALLMEBOT_APIKEY` — your CallMeBot API key
