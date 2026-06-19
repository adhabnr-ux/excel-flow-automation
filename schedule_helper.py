#!/usr/bin/env python3
"""Shared logic for deciding which posts can be scheduled natively.

A "schedulable" post is one you can load into LinkedIn's (or Substack's) own
built-in scheduler so it publishes server-side at the right time — no live tap
needed, no ToS risk, no browser bot.

What is natively schedulable in practice:
  - LinkedIn TEXT posts (Creator Shoutouts, plain commentary) — YES, fully.
  - LinkedIn POLLS — NO. LinkedIn's scheduler does not reliably support polls.
  - Substack full editions — YES (but those are not in the daily content files).
  - Substack daily Notes — NO native scheduling.

So by default only LinkedIn non-poll posts are treated as schedulable. You can
override per-post by adding  "schedulable": true  or  "schedulable": false  to
any post in the content JSON (e.g. if you run a LinkedIn "poll" as a plain text
post to chase comments, mark it schedulable to batch it on Sunday).
"""

# LinkedIn post types that are plain text (no native poll widget) => schedulable.
SCHEDULABLE_LINKEDIN_TYPES = {"Creator Shoutout", "Shoutout", "Text", "Article"}


def is_schedulable(post):
    """True if this post can be loaded into a platform's native scheduler."""
    if "schedulable" in post:
        return bool(post["schedulable"])
    # Default heuristic — conservative: only LinkedIn plain-text posts.
    return (
        post.get("platform") == "LinkedIn"
        and post.get("type") in SCHEDULABLE_LINKEDIN_TYPES
    )
