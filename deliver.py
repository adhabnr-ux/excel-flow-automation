#!/usr/bin/env python3
"""Excel Flow delivery — run by GitHub Actions on a schedule.

Usage:  python3 deliver.py <Morning|Midday|Evening>

Reads every content/week-*.json, finds the posts dated today (America/Phoenix)
in the given window, QA-checks them, and sends each as a WhatsApp message via
CallMeBot. Fully deterministic — no AI, no rewriting. Post content is delivered
byte-for-byte. Carousels are pre-rendered PDFs already committed under
carousels/; their public raw URL is delivered.

Environment:
  CALLMEBOT_PHONE    CallMeBot phone number   (from GitHub Secrets)
  CALLMEBOT_APIKEY   CallMeBot API key        (from GitHub Secrets)
  GITHUB_REPOSITORY  owner/repo               (set automatically by Actions)
  GITHUB_REF_NAME    branch name              (set automatically by Actions)
"""
import datetime
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

PHONE = os.environ.get("CALLMEBOT_PHONE", "").strip()
APIKEY = os.environ.get("CALLMEBOT_APIKEY", "").strip()
REPO = os.environ.get("GITHUB_REPOSITORY", "").strip()
REF = os.environ.get("GITHUB_REF_NAME", "main").strip() or "main"

MST = datetime.timezone(datetime.timedelta(hours=-7))  # America/Phoenix, no DST
GAP = 30  # seconds between WhatsApp messages (stays within CallMeBot limits)

RE_PLACEHOLDER = re.compile(r"(?<!\w)\[[^\]\n]+\]")
RE_URL = re.compile(r"https?://[^\s)]+")
RE_OPTION = re.compile(r"^[A-Z]\)\s*(.+)$")


def log(*a):
    print(*a, flush=True)


def send_whatsapp(text):
    """Send one WhatsApp message via CallMeBot. Retries up to 3x. Returns bool."""
    query = urllib.parse.urlencode({"phone": PHONE, "apikey": APIKEY, "text": text})
    url = "https://api.callmebot.com/whatsapp.php?" + query
    for attempt in (1, 2, 3):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                body = r.read().decode("utf-8", "ignore")
                if r.status == 200:
                    return True
                log(f"  send attempt {attempt}: HTTP {r.status} {body[:120]}")
        except Exception as e:
            log(f"  send attempt {attempt} failed: {e}")
        time.sleep(10)
    return False


def url_alive(u):
    """True if the URL responds 200. Tries HEAD, falls back to GET."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(
                u, method=method, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status == 200
        except Exception:
            continue
    return False


def qa(post):
    """Return a list of QA warning strings for a post (empty == clean)."""
    flags = []
    text = (post.get("content") or "") + "\n" + (post.get("first_comment") or "")
    for ph in sorted(set(RE_PLACEHOLDER.findall(text))):
        flags.append(f"unresolved placeholder {ph} - fix before posting")
    if post["platform"] == "LinkedIn" and "Poll" in post["type"]:
        for line in (post.get("content") or "").split("\n"):
            m = RE_OPTION.match(line.strip())
            if m and len(m.group(1)) > 30:
                flags.append(f"LinkedIn poll option is {len(m.group(1))} chars "
                             f"(max 30) - trim: {m.group(1)}")
    for u in sorted(set(RE_URL.findall(text))):
        if not url_alive(u):
            flags.append(f"link not reachable: {u}")
    return flags


def carousel_url(post):
    path = post.get("carousel_pdf")
    if not path or not REPO:
        return None
    return f"https://raw.githubusercontent.com/{REPO}/{REF}/{path}"


def messages_for(post, flags):
    """Build the ordered WhatsApp messages for one post.

    Every post sends as two bubbles: (1) header/instructions, (2) content only.
    This lets the user long-press bubble 2 and copy clean text with no metadata.
    """
    plat = post["platform"]
    flagblock = "".join("\n⚠️ " + f for f in flags)
    msgs = []

    if post["type"] == "Carousel":
        link = carousel_url(post) or "(carousel PDF link unavailable)"
        # Bubble 1 — instructions + PDF link (not copy-pasteable, keep together)
        msgs.append(
            f"📅 EXCEL FLOW\n{plat} · {post['post_time_display']} · CAROUSEL POST"
            f"{flagblock}\n\n🎨 Download this PDF, then upload to LinkedIn as a "
            f"document post:\n{link}")
        # Bubble 2 — caption label
        msgs.append(f"📅 EXCEL FLOW · CAROUSEL CAPTION\n{plat} · {post['post_time_display']} · copy this into the post text 👇")
        # Bubble 3 — clean caption content only
        msgs.append(post["content"])
        if post.get("first_comment"):
            # Bubble 4 — first comment label
            msgs.append(f"📅 EXCEL FLOW · CAROUSEL FIRST COMMENT\nPost within 60s of publishing 👇")
            # Bubble 5 — clean first comment content only
            msgs.append(post["first_comment"])
        return msgs

    # Bubble 1 — header + context (platform, time, type, QA flags)
    head = f"📅 EXCEL FLOW\n{plat} · {post['post_time_display']} · {post['type']}"
    msgs.append(f"{head}{flagblock}")
    # Bubble 2 — clean content only (long-press and copy this)
    msgs.append(post["content"])
    if post.get("is_test_poll") and post.get("first_comment"):
        when = post.get("first_comment_time_display") or "right after the poll"
        # Bubble 3 — first comment label
        msgs.append(f"📅 EXCEL FLOW · FIRST COMMENT\n{plat} · post within 60s, at {when} 👇")
        # Bubble 4 — clean first comment content only
        msgs.append(post["first_comment"])
    return msgs


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("Morning", "Midday", "Evening"):
        sys.exit("Usage: python3 deliver.py <Morning|Midday|Evening>")
    window = sys.argv[1]
    today = datetime.datetime.now(MST).strftime("%Y-%m-%d")
    log(f"Excel Flow delivery — window={window} date={today} (America/Phoenix)")

    if not PHONE or not APIKEY:
        sys.exit("ERROR: CALLMEBOT_PHONE / CALLMEBOT_APIKEY not set in Secrets.")

    posts = []
    for f in sorted(glob.glob("content/week-*.json")):
        posts += json.load(open(f, encoding="utf-8")).get("posts", [])
    batch = sorted(
        [p for p in posts if p["date"] == today and p["window"] == window],
        key=lambda p: p["post_time"])
    log(f"{len(batch)} post(s) in batch: {[p['id'] for p in batch]}")

    if not batch:
        send_whatsapp(f"📅 EXCEL FLOW\nNothing scheduled for the {window.lower()} "
                      f"window today ({today}).")
        return

    flags = {p["id"]: qa(p) for p in batch}

    queue = []
    for p in batch:
        queue += messages_for(p, flags[p["id"]])
    if len(batch) > 5:
        queue.append(f"📅 EXCEL FLOW\n⚠️ unusually large batch ({len(batch)} "
                     f"posts) — check the content file.")
    queue[-1] += f"\n— batch: {len(batch)} post(s) delivered."

    sent = 0
    for i, m in enumerate(queue):
        ok = send_whatsapp(m)
        sent += ok
        log(f"message {i + 1}/{len(queue)}: {'sent' if ok else 'FAILED'}")
        if i < len(queue) - 1:
            time.sleep(GAP)

    # Full report -> visible in the Actions run log. This is the fallback if a
    # WhatsApp message did not arrive.
    log("\n===== FULL BATCH REPORT (fallback) =====")
    for p in batch:
        log(f"\n--- {p['id']} | {p['platform']} | {p['post_time_display']} | "
            f"{p['type']}")
        for fl in flags[p["id"]]:
            log(f"  QA: {fl}")
        log(p["content"])
        if p.get("first_comment"):
            log(f"  [first comment]\n{p['first_comment']}")
        if p.get("carousel_pdf"):
            log(f"  [carousel] {carousel_url(p)}")
    log(f"\n{sent}/{len(queue)} messages delivered.")

    if sent < len(queue):
        sys.exit(1)  # fail the run so GitHub emails you about the miss


if __name__ == "__main__":
    main()
