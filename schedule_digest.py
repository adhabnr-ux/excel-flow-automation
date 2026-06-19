#!/usr/bin/env python3
"""Sunday scheduling digest — Telegram push of the coming week's schedulable posts.

For every post that can be loaded into LinkedIn's native scheduler (see
schedule_helper.is_schedulable), this sends a copy-ready Telegram message with
the exact day/date/time to set. You sit down once on Sunday, paste each into
LinkedIn's scheduler, and that whole category of posts publishes itself all
week — server-side, computer off, zero ToS risk. Polls still come via the live
deliver.py tap because they cannot be natively scheduled.

Usage:
    python3 schedule_digest.py                       # upcoming week (next Monday)
    python3 schedule_digest.py content/week-2026-06-15.json
    python3 schedule_digest.py --dry-run             # print, do not send
"""
import datetime
import glob
import json
import os
import sys

from deliver import send_telegram, load_editions, resolve_edition_links, log
from schedule_helper import is_schedulable

MST = datetime.timezone(datetime.timedelta(hours=-7))
GAP = 2


def upcoming_week_file():
    """Path to the content file for the week that is about to start (next Monday)."""
    today = datetime.datetime.now(MST).date()
    days_ahead = (0 - today.weekday()) % 7  # 0=Mon today, else days until next Mon
    if days_ahead == 0:
        days_ahead = 0  # run on a Monday => this week
    monday = today + datetime.timedelta(days=days_ahead)
    return f"content/week-{monday.isoformat()}.json"


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    explicit = [a for a in args if not a.startswith("--")]

    path = explicit[0] if explicit else upcoming_week_file()
    if not os.path.exists(path):
        # Fall back to the most recent week file so the digest never silently no-ops.
        candidates = sorted(glob.glob("content/week-*.json"))
        if not candidates:
            log(f"No content files found; nothing to schedule.")
            return
        log(f"{path} not found — using latest available: {candidates[-1]}")
        path = candidates[-1]

    with open(path, encoding="utf-8") as f:
        posts = json.load(f).get("posts", [])

    editions = load_editions()
    schedulable = sorted(
        [p for p in posts if is_schedulable(p)],
        key=lambda p: (p["date"], p["post_time"]),
    )

    log(f"Scheduling digest for {path}: {len(schedulable)} schedulable post(s).")

    if not schedulable:
        header = ("📆 EXCEL FLOW — WEEKLY SCHEDULING\n"
                  f"No natively-schedulable posts in {os.path.basename(path)}.\n"
                  "Everything this week is a poll/Note — those come via the live tap.")
        if dry_run:
            log(f"[DRY-RUN] {header}")
            return
        send_telegram(header)
        return

    header = (
        "📆 EXCEL FLOW — SCHEDULE THESE NOW\n"
        f"{len(schedulable)} LinkedIn post(s) for the week of "
        f"{schedulable[0]['date']}.\n\n"
        "Open LinkedIn → New post → write/paste → click the 🕒 clock → set the "
        "date & time shown below → Schedule. Do all of them in one sitting and "
        "they publish themselves all week.\n"
        "(Polls are not listed — LinkedIn can't schedule those, so they still "
        "come as a live tap at post time.)"
    )

    messages = [header]
    for p in schedulable:
        content = resolve_edition_links(p.get("content") or "", editions)
        when = f"{p['day']} {p['date']} · {p['post_time_display']}"
        messages.append(f"🕒 SCHEDULE FOR: {when}\n{p['platform']} · {p['type']}\n👇 copy the message below as the post text")
        messages.append(content)
        if p.get("first_comment"):
            fc = resolve_edition_links(p["first_comment"], editions)
            fc_when = p.get("first_comment_time_display") or "right after"
            messages.append(f"💬 FIRST COMMENT for the above (post at {fc_when}) 👇")
            messages.append(fc)

    import time
    sent = 0
    for i, m in enumerate(messages):
        if dry_run:
            log(f"\n[DRY-RUN] {i+1}/{len(messages)} ({len(m)} chars):\n{m}\n{'─'*60}")
            sent += 1
            continue
        if send_telegram(m):
            sent += 1
        if i < len(messages) - 1:
            time.sleep(GAP)

    log(f"\n{sent}/{len(messages)} digest message(s) {'previewed' if dry_run else 'sent'}.")
    if not dry_run and sent < len(messages):
        sys.exit(1)


if __name__ == "__main__":
    main()
