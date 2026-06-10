#!/usr/bin/env python3
"""Scaffold a new week content file with all post slots pre-populated.

Usage:
    python3 scripts/new_week.py 2026-06-15        # creates content/week-2026-06-15.json
    python3 scripts/new_week.py 2026-06-15 --dry  # print to stdout, don't write

The start date must be a Monday. The script generates 44 posts across 7 days
matching the standard Excel Flow weekly schedule (LinkedIn + Substack).
"""
import datetime
import json
import os
import sys

# ── Weekly schedule template ────────────────────────────────────────────────
# Each entry: (day_offset, time_str, platform, post_type, window, is_test_poll)
# day_offset 0 = Monday, 6 = Sunday
SCHEDULE = [
    # Monday
    (0, "07:30", "LinkedIn",  "Poll",              "Morning", True),
    (0, "12:00", "LinkedIn",  "This or That Poll", "Midday",  False),
    (0, "17:30", "LinkedIn",  "Poll",              "Evening", False),
    (0, "20:00", "Substack",  "Poll",              "Evening", False),
    (0, "20:30", "Substack",  "Quick Fix",         "Evening", False),
    (0, "21:00", "Substack",  "Reader Question",   "Evening", False),
    # Tuesday
    (1, "07:30", "LinkedIn",  "Poll",              "Morning", True),
    (1, "09:00", "LinkedIn",  "Creator Shoutout",  "Morning", False),
    (1, "12:00", "LinkedIn",  "This or That Poll", "Midday",  False),
    (1, "17:30", "LinkedIn",  "Poll",              "Evening", False),
    (1, "19:00", "Substack",  "Poll",              "Evening", False),
    (1, "19:30", "Substack",  "Quick Fix",         "Evening", False),
    (1, "20:00", "Substack",  "Reader Question",   "Evening", False),
    # Wednesday
    (2, "07:30", "LinkedIn",  "Poll",              "Morning", True),
    (2, "08:00", "Substack",  "Poll",              "Morning", False),
    (2, "12:00", "LinkedIn",  "Poll",              "Midday",  False),
    (2, "12:00", "Substack",  "Quick Fix",         "Midday",  False),
    (2, "17:30", "LinkedIn",  "This or That Poll", "Evening", False),
    (2, "20:00", "Substack",  "Reader Question",   "Evening", False),
    # Thursday
    (3, "07:30", "LinkedIn",  "Poll",              "Morning", True),
    (3, "09:00", "LinkedIn",  "Creator Shoutout",  "Morning", False),
    (3, "12:00", "LinkedIn",  "Poll",              "Midday",  False),
    (3, "17:30", "LinkedIn",  "This or That Poll", "Evening", False),
    (3, "18:00", "Substack",  "Poll",              "Evening", False),
    (3, "18:30", "Substack",  "Quick Fix",         "Evening", False),
    (3, "19:00", "Substack",  "Reader Question",   "Evening", False),
    # Friday
    (4, "07:30", "LinkedIn",  "Poll",              "Morning", True),
    (4, "12:00", "LinkedIn",  "Poll",              "Midday",  False),
    (4, "17:30", "LinkedIn",  "Poll",              "Evening", False),
    (4, "19:00", "Substack",  "Poll",              "Evening", False),
    (4, "19:30", "Substack",  "Quick Fix",         "Evening", False),
    (4, "20:00", "Substack",  "Reader Question",   "Evening", False),
    # Saturday
    (5, "09:00", "LinkedIn",  "Poll",              "Morning", False),
    (5, "11:00", "LinkedIn",  "This or That Poll", "Midday",  False),
    (5, "13:00", "LinkedIn",  "Poll",              "Midday",  False),
    (5, "16:30", "Substack",  "Poll",              "Evening", False),
    (5, "17:00", "Substack",  "Quick Fix",         "Evening", False),
    (5, "17:30", "Substack",  "Reader Question",   "Evening", False),
    # Sunday
    (6, "10:00", "LinkedIn",  "Poll",              "Morning", False),
    (6, "12:00", "LinkedIn",  "This or That Poll", "Midday",  False),
    (6, "18:00", "LinkedIn",  "Poll",              "Evening", False),
    (6, "19:30", "Substack",  "Poll",              "Evening", False),
    (6, "20:00", "Substack",  "Quick Fix",         "Evening", False),
    (6, "20:30", "Substack",  "Reader Question",   "Evening", False),
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PLAT_SHORT = {"LinkedIn": "li", "Substack": "ss"}
TYPE_SHORT = {
    "Poll": "poll",
    "This or That Poll": "tot",
    "Creator Shoutout": "shout",
    "Quick Fix": "qf",
    "Reader Question": "rq",
}

def time_to_display(t):
    h, m = map(int, t.split(":"))
    suffix = "AM" if h < 12 else "PM"
    h12 = h if h <= 12 else h - 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {suffix}"

def day_abbr(day):
    return day[:3].lower()

def make_id(day, offset, platform, ptype, time_str):
    abbr = day_abbr(DAYS[offset])
    plat = PLAT_SHORT.get(platform, platform[:2].lower())
    t = time_str.replace(":", "")
    return f"{abbr}-{plat}-{t}"

def scaffold(start_date_str, dry=False):
    try:
        start = datetime.date.fromisoformat(start_date_str)
    except ValueError:
        sys.exit(f"ERROR: Invalid date {start_date_str!r}. Use YYYY-MM-DD.")

    if start.weekday() != 0:
        actual_monday = start - datetime.timedelta(days=start.weekday())
        print(f"WARNING: {start_date_str} is a {DAYS[start.weekday()]}. "
              f"Snapping to Monday {actual_monday}.", file=sys.stderr)
        start = actual_monday

    posts = []
    seen_ids = {}
    for (offset, time_str, platform, ptype, window, is_test) in SCHEDULE:
        date = start + datetime.timedelta(days=offset)
        date_str = date.isoformat()
        day = DAYS[offset]
        pid = make_id(day, offset, platform, ptype, time_str)

        # Deduplicate IDs (e.g. two 12:00 posts same day/platform)
        if pid in seen_ids:
            seen_ids[pid] += 1
            pid = f"{pid}-{seen_ids[pid]}"
        else:
            seen_ids[pid] = 0

        post = {
            "id": pid,
            "date": date_str,
            "day": day,
            "post_time": time_str,
            "post_time_display": time_to_display(time_str),
            "window": window,
            "platform": platform,
            "type": ptype,
            "content": "",
        }
        if is_test:
            post["first_comment"] = ""
            post["first_comment_time_display"] = time_to_display(
                f"{int(time_str.split(':')[0]):02d}:{int(time_str.split(':')[1])+1:02d}"
            )
            post["is_test_poll"] = True

        posts.append(post)

    data = {"week": start_date_str, "posts": posts}
    output = json.dumps(data, indent=2, ensure_ascii=False)

    if dry:
        print(output)
        return

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "content",
        f"week-{start_date_str}.json",
    )
    if os.path.exists(out_path):
        sys.exit(f"ERROR: {out_path} already exists. Delete it first if you want to regenerate.")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"Created {out_path} ({len(posts)} posts)")
    print("Next steps:")
    print("  1. Fill in 'content' fields for each post")
    print("  2. Fill 'first_comment' for is_test_poll posts")
    print("  3. Run: python3 validate.py to check for errors")
    print("  4. git add + commit + push")


def main():
    args = sys.argv[1:]
    dry = "--dry" in args
    dates = [a for a in args if not a.startswith("--")]
    if len(dates) != 1:
        sys.exit("Usage: python3 scripts/new_week.py YYYY-MM-DD [--dry]")
    scaffold(dates[0], dry=dry)


if __name__ == "__main__":
    main()
