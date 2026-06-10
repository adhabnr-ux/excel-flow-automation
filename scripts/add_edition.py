#!/usr/bin/env python3
"""Register a Substack URL for an edition number in editions.json.

Usage:
    python3 scripts/add_edition.py 31 https://rileystream.substack.com/p/slug

Adds the key if it does not exist. Updates it if it does.
Commits and prints a reminder to push.
"""
import json
import os
import sys

EDITIONS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "editions.json")


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python3 scripts/add_edition.py <edition_number> <url>")

    edition = sys.argv[1].lstrip("#")
    url = sys.argv[2].strip()

    if not edition.isdigit():
        sys.exit(f"ERROR: Edition number must be a number, got {edition!r}")
    if not url.startswith("http"):
        sys.exit(f"ERROR: URL must start with http, got {url!r}")

    with open(EDITIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    old = data["editions"].get(edition)
    data["editions"][edition] = url

    with open(EDITIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if old:
        print(f"Updated Edition #{edition}: {old!r} → {url!r}")
    else:
        print(f"Added Edition #{edition}: {url!r}")

    print(f"Run: git add editions.json && git commit -m 'add edition #{edition} URL' && git push")


if __name__ == "__main__":
    main()
