#!/usr/bin/env python3
"""Validate all content/week-*.json files against the expected schema.

Usage:
    python3 validate.py              # validate all week files
    python3 validate.py content/week-2026-06-08.json  # validate one file

Exit code 0 = all valid (warnings OK). Exit code 1 = one or more errors.
"""
import glob
import json
import os
import re
import sys

VALID_WINDOWS = {"Morning", "Midday", "Evening"}
VALID_PLATFORMS = {"LinkedIn", "Substack"}
VALID_DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
VALID_TYPES = {
    "Poll", "This or That Poll", "Creator Shoutout", "Shoutout",
    "Quick Fix", "Reader Question", "Carousel",
}
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_TIME = re.compile(r"^\d{2}:\d{2}$")
RE_PLACEHOLDER = re.compile(r"(?<!\w)\[[^\]\n]+\]")


def validate_file(path):
    errors = []
    warnings = []

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON parse error: {e}"], []

    if not isinstance(data.get("posts"), list):
        return ["Missing or non-list 'posts' key at top level"], []

    seen_ids = {}
    for i, post in enumerate(data["posts"]):
        loc = f"post[{i}] id={post.get('id', '?')!r}"

        # Required string fields
        for field in ("id", "date", "day", "post_time", "post_time_display", "platform", "type", "content"):
            val = post.get(field)
            if not val or not isinstance(val, str):
                errors.append(f"{loc}: missing or empty required field '{field}'")

        pid = post.get("id", "")
        if pid:
            if pid in seen_ids:
                errors.append(f"{loc}: duplicate id '{pid}' (first seen at post[{seen_ids[pid]}])")
            else:
                seen_ids[pid] = i

        date = post.get("date", "")
        if date and not RE_DATE.match(date):
            errors.append(f"{loc}: 'date' must be YYYY-MM-DD, got {date!r}")

        pt = post.get("post_time", "")
        if pt and not RE_TIME.match(pt):
            errors.append(f"{loc}: 'post_time' must be HH:MM (24h), got {pt!r}")

        window = post.get("window", "")
        if window and window not in VALID_WINDOWS:
            errors.append(f"{loc}: 'window' must be one of {sorted(VALID_WINDOWS)}, got {window!r}")

        platform = post.get("platform", "")
        if platform and platform not in VALID_PLATFORMS:
            errors.append(f"{loc}: 'platform' must be one of {sorted(VALID_PLATFORMS)}, got {platform!r}")

        day = post.get("day", "")
        if day and day not in VALID_DAYS:
            warnings.append(f"{loc}: 'day' {day!r} not a standard day name (non-blocking)")

        ptype = post.get("type", "")
        if ptype and ptype not in VALID_TYPES:
            warnings.append(f"{loc}: 'type' {ptype!r} not in known types {sorted(VALID_TYPES)} (non-blocking)")

        if post.get("is_test_poll") and not post.get("first_comment"):
            errors.append(f"{loc}: is_test_poll=true but no 'first_comment' field")

        # QA placeholder check
        text = (post.get("content") or "") + "\n" + (post.get("first_comment") or "")
        placeholders = sorted(set(RE_PLACEHOLDER.findall(text)))
        for ph in placeholders:
            warnings.append(f"{loc}: unresolved placeholder {ph}")

    return errors, warnings


def main():
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        files = sys.argv[1:]
    else:
        files = sorted(glob.glob("content/week-*.json"))

    if not files:
        print("No content files found.")
        sys.exit(0)

    total_errors = 0
    total_warnings = 0

    for path in files:
        errors, warnings = validate_file(path)
        label = os.path.basename(path)
        if errors or warnings:
            print(f"\n{'='*60}")
            print(f"  {label}")
            print(f"{'='*60}")
        if errors:
            for e in errors:
                print(f"  ❌ ERROR: {e}")
            total_errors += len(errors)
        if warnings:
            for w in warnings:
                print(f"  ⚠️  WARN:  {w}")
            total_warnings += len(warnings)
        if not errors and not warnings:
            print(f"  ✅ {label} — clean")

    print(f"\n{'─'*60}")
    print(f"Validated {len(files)} file(s): {total_errors} error(s), {total_warnings} warning(s).")
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
