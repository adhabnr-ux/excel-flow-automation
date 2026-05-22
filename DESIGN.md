# Excel Flow — Posting Automation — Design Spec

**Date:** 2026-05-21
**Owner:** Excel Flow (user)
**Status:** Built — runs on GitHub Actions

---

## 1. Problem & Goal

Excel Flow publishes **3 posts/day on LinkedIn + 3/day on Substack = 42/week**.
Goal: automate posting with 100% content accuracy, minimal manual effort, and no
dependence on the user's computer being on.

## 2. The hard constraint (why this is not "auto-post")

- **LinkedIn's API cannot create polls.** 18 of 21 weekly LinkedIn posts are
  polls. Polls are UI-only — no tool can post them.
- **Substack has no public posting API.** All 21 Notes are UI-only.

True lights-out auto-posting is impossible. This system is **prep-and-deliver**:
it assembles every post perfectly and delivers it ready-to-paste at the right
time; the user does the final publish tap (~20–30s/post).

## 3. Architecture — two layers

- **Layer 1 — Brain (in chat, weekly):** content creation. The user + Claude
  generate the week's 42 posts. The user hands new content to Claude each week;
  Claude commits it to the repo. Not part of the automated runtime.
- **Layer 2 — Hands (this system):** a deterministic delivery script run by
  GitHub Actions on a schedule. No AI at delivery time — that is what guarantees
  100% content accuracy.

## 4. Why GitHub Actions

The delivery layer is fully deterministic (fetch → filter → QA → send). A plain
script running on GitHub Actions executes identically every time, is free, and
runs on GitHub's servers — independent of the user's computer. No AI agent is
needed or wanted at delivery time.

## 5. Components

1. **Content store** — `content/week-*.json`, one file per week, committed to
   the repo. One object per post (42/week). `deliver.py` reads every matching
   file directly from the checked-out repo.
2. **`deliver.py`** — the delivery script. Python standard library only.
3. **GitHub Actions workflow** — `.github/workflows/deliver.yml`. Three cron
   schedules + a manual `workflow_dispatch` trigger for tests.
4. **Carousels** — pre-rendered PDFs committed under `carousels/`. Delivered as
   `raw.githubusercontent.com` links. `carousel-renderer.py` (Python + fpdf2)
   regenerates them from each carousel's spec; run locally when content changes.
5. **Delivery channel** — CallMeBot WhatsApp API, using the user's existing key,
   stored in GitHub Actions Secrets.

## 6. Schedule

Cron is UTC; America/Phoenix is UTC-7 with no daylight saving, so these are
stable year-round.

| Window  | Cron (UTC)    | Local (MST) | Delivers posts timed |
|---------|---------------|-------------|----------------------|
| Morning | `30 13 * * *` | 06:30       | before 12:00         |
| Midday  | `0 18 * * *`  | 11:00       | 12:00–16:59          |
| Evening | `0 23 * * *`  | 16:00       | 17:00 and later      |

Each fires 60–90 min before its earliest post — absorbs any GitHub cron delay.

## 7. `deliver.py` logic

1. Read the window argument (`Morning` / `Midday` / `Evening`).
2. Compute today's date in America/Phoenix (fixed UTC-7).
3. Load every `content/week-*.json`, merge posts, select `date == today` and
   `window == this window`, sort by `post_time`. → BATCH.
4. If BATCH is empty: send one "nothing scheduled" WhatsApp; exit.
5. QA each post (flags only — never blocks delivery):
   - LinkedIn poll options over 30 characters.
   - Leftover `[...]` placeholders in content / first comment.
   - Any URL that does not return HTTP 200.
6. Build messages — one WhatsApp message per post, `📅 EXCEL FLOW` header,
   QA flags inline. Test polls get a second message (the first comment).
   Carousels get up to three (link + caption + first comment).
7. Send each via CallMeBot, 30s apart, 3 retries each.
8. Print the full batch report to the run log (the fallback if WhatsApp misses).
9. Exit non-zero if any message failed — GitHub emails the user on a failed run.

## 8. Error handling

- QA failure → post still delivered, flagged `⚠️` in the message.
- CallMeBot send failure → 3 retries; full batch is in the run log; the run is
  marked failed so GitHub notifies the user.
- Carousel link unavailable → message says so; the run log carries the detail.

## 9. What stays manual (unavoidable)

- The publish tap on LinkedIn / Substack.
- Uploading the carousel PDF into LinkedIn (script delivers the link; upload is
  manual).
- Filling real Substack edition URLs into weekly content (QA flags placeholders).

## 10. Accuracy statement

- **Content: 100%** — verbatim from the content JSON; the script never edits it.
- **Carousel slides: 100%** — text and colors rendered deterministically from
  the spec (templated, not generative AI).
- **Delivery: best-effort** — CallMeBot is a free relay; the run log is the
  fallback and a failed run emails the user.

## 11. Known content issue

Several LinkedIn poll options exceed LinkedIn's 30-character limit (e.g. "Check
the formulas before touching anything" = 43 chars). LinkedIn rejects longer
options. QA flags them; trim during weekly content creation.

## 12. Inputs needed from the user

1. CallMeBot **phone number + API key** → GitHub Secrets `CALLMEBOT_PHONE`,
   `CALLMEBOT_APIKEY`.
2. Excel Flow Substack **edition URLs** (#18, #23, #25, #26, #27, #28, #29).
3. The user's **LinkedIn display name + handle** (carousel slide footers).

## 13. Repo & weekly workflow

- Public GitHub repo. Code + content + carousels live in it. Only the CallMeBot
  credentials are secret (encrypted Actions Secrets).
- Weekly: the user pastes new content to Claude in chat → Claude rewrites
  `content/`, re-renders `carousels/`, commits, and pushes. The workflow and
  `deliver.py` never change.
