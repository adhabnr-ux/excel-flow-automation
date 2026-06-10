#!/usr/bin/env python3
"""Send the Sunday weekly metrics reminder to Telegram.

Run by GitHub Actions every Sunday at 04:00 UTC (9 PM MST, no DST).
"""
import datetime
import json
import os
import sys
import time
import urllib.request

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
MST = datetime.timezone(datetime.timedelta(hours=-7))


def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": CHAT_ID, "text": text}).encode()
    for attempt in (1, 2, 3):
        try:
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "ignore")
                result = json.loads(body)
                if result.get("ok"):
                    return True
                print(f"  attempt {attempt}: Telegram error — {result.get('description', body[:120])}", flush=True)
        except Exception as e:
            print(f"  attempt {attempt} failed: {e}", flush=True)
        time.sleep(5)
    return False


def main():
    if not BOT_TOKEN or not CHAT_ID:
        sys.exit("ERROR: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.")

    today = datetime.datetime.now(MST)
    week_end = today.strftime("%B %-d")

    msg = f"""📊 EXCEL FLOW — WEEKLY METRICS
Sunday {week_end} · Pull these now

LINKEDIN (check LinkedIn Analytics)
□ Total impressions this week
  → Target: 350K+ | Best week: 300K
□ Highest-vote poll — note the exact hook
□ Highest-comment post — any post over 50 comments gets replicated next week
□ Best time slot — log every post that hit over 15K impressions

SUBSTACK (check Substack Stats → Traffic Sources)
□ New subscribers this week vs last week
□ Edition link click-throughs from LinkedIn
□ Top traffic source this week

CREATOR SHOUTOUTS
□ Did Luke Barousse or Jeff Lenning engage, comment, or reshare?

NEXT WEEK ACTIONS
□ Replicate any post that broke 75 comments (different topic, same format)
□ Add any missing edition links to editions.json
□ Run: python3 validate.py before Monday

The single most important number: comments per post, not votes.
Comments = algorithm shows post to non-followers → 350K comes from there."""

    ok = send_telegram(msg)
    print(f"Metrics reminder: {'sent' if ok else 'FAILED'}", flush=True)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
