#!/usr/bin/env python3
"""Excel Flow delivery — run by GitHub Actions on a schedule.

Usage:  python3 deliver.py <Morning|Midday|Evening>

Reads every content/week-*.json, finds the posts dated today (America/Phoenix)
in the given window, QA-checks them, and sends each as a Telegram message via
the Bot API. Fully deterministic — no AI, no rewriting. Post content is
delivered byte-for-byte. Carousels are pre-rendered PDFs already committed
under carousels/; their public raw URL is delivered.

Environment:
  TELEGRAM_BOT_TOKEN  Telegram bot token         (from GitHub Secrets)
  TELEGRAM_CHAT_ID    Telegram chat/user ID      (from GitHub Secrets)
  GITHUB_REPOSITORY   owner/repo                 (set automatically by Actions)
  GITHUB_REF_NAME     branch name                (set automatically by Actions)
"""
import datetime
import glob
import json
import os
import re
import sys
import time
import urllib.request

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
REPO = os.environ.get("GITHUB_REPOSITORY", "").strip()
REF = os.environ.get("GITHUB_REF_NAME", "main").strip() or "main"

MST = datetime.timezone(datetime.timedelta(hours=-7))  # America/Phoenix, no DST
GAP = 2  # seconds between Telegram messages (no rate issues, small gap for ordering)

RE_PLACEHOLDER = re.compile(r"(?<!\w)\[[^\]\n]+\]")
RE_OPTION = re.compile(r"^[A-Z]\)\s*(.+)$")
RE_EDITION_BLOCK = re.compile(r"(Edition #(\d+)[^\n]*)\n\[link\]")
RE_EDITION_INLINE = re.compile(r"\[Edition #(\d+) link\]")


def load_editions():
    """Load editions.json from the repo root. Returns dict of {str: url_or_None}."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editions.json")
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("editions", {})
    except Exception:
        return {}


def resolve_edition_links(text, editions):
    """Replace [link] / [Edition #N link] with known URLs. Unknown editions stay as-is."""
    def sub_block(m):
        url = editions.get(m.group(2))
        return f"{m.group(1)}\n{url}" if url else m.group(0)

    def sub_inline(m):
        url = editions.get(m.group(1))
        return url if url else m.group(0)

    text = RE_EDITION_BLOCK.sub(sub_block, text)
    text = RE_EDITION_INLINE.sub(sub_inline, text)
    return text


def log(*a):
    print(*a, flush=True)


def send_telegram(text):
    """Send one Telegram message via Bot API. Retries up to 3x. Returns bool."""
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
                log(f"  send attempt {attempt}: Telegram error — {result.get('description', body[:120])}")
        except Exception as e:
            log(f"  send attempt {attempt} failed: {e}")
        time.sleep(5)
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
    return flags


def carousel_url(post):
    path = post.get("carousel_pdf")
    if not path or not REPO:
        return None
    return f"https://raw.githubusercontent.com/{REPO}/{REF}/{path}"


def messages_for(post, flags):
    """Build the ordered Telegram messages for one post.

    Every post sends as two messages: (1) header/instructions, (2) content only.
    Tap-and-hold message 2 to copy clean text with no metadata.
    """
    plat = post["platform"]
    flagblock = "".join("\n⚠️ " + f for f in flags)
    msgs = []

    if post["type"] == "Carousel":
        link = carousel_url(post) or "(carousel PDF link unavailable)"
        msgs.append(
            f"📅 EXCEL FLOW\n{plat} · {post['post_time_display']} · CAROUSEL POST"
            f"{flagblock}\n\n🎨 Download this PDF, then upload to LinkedIn as a "
            f"document post:\n{link}")
        msgs.append(f"📅 EXCEL FLOW · CAROUSEL CAPTION\n{plat} · {post['post_time_display']} · copy this into the post text 👇")
        msgs.append(post["content"])
        if post.get("first_comment"):
            msgs.append("📅 EXCEL FLOW · CAROUSEL FIRST COMMENT\nPost within 60s of publishing 👇")
            msgs.append(post["first_comment"])
        return msgs

    head = f"📅 EXCEL FLOW\n{plat} · {post['post_time_display']} · {post['type']}"
    msgs.append(f"{head}{flagblock}")
    msgs.append(post["content"])
    if post.get("is_test_poll") and post.get("first_comment"):
        when = post.get("first_comment_time_display") or "right after the poll"
        msgs.append(f"📅 EXCEL FLOW · FIRST COMMENT\n{plat} · post within 60s, at {when} 👇")
        msgs.append(post["first_comment"])
    return msgs


def main():
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    if len(positional) != 1 or positional[0] not in ("Morning", "Midday", "Evening"):
        sys.exit("Usage: python3 deliver.py <Morning|Midday|Evening> [--dry-run]")
    window = positional[0]
    today = datetime.datetime.now(MST).strftime("%Y-%m-%d")
    log(f"Excel Flow delivery — window={window} date={today} (America/Phoenix)")
    if dry_run:
        log("*** DRY-RUN MODE — no messages will be sent ***")

    if not dry_run and (not BOT_TOKEN or not CHAT_ID):
        sys.exit("ERROR: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set in Secrets.")

    log(f"Telegram: bot token set={bool(BOT_TOKEN)}  chat_id={CHAT_ID[:3] if len(CHAT_ID)>=3 else '?'}...{CHAT_ID[-3:] if len(CHAT_ID)>=3 else '?'} (len={len(CHAT_ID)})")

    editions = load_editions()
    log(f"Edition registry: {len(editions)} entries, {sum(1 for v in editions.values() if v)} with URLs")

    posts = []
    for f in sorted(glob.glob("content/week-*.json")):
        posts += json.load(open(f, encoding="utf-8")).get("posts", [])
    batch = sorted(
        [p for p in posts if p["date"] == today and p["window"] == window],
        key=lambda p: p["post_time"])
    log(f"{len(batch)} post(s) in batch: {[p['id'] for p in batch]}")

    if not batch:
        msg = f"📅 EXCEL FLOW\nNothing scheduled for the {window.lower()} window today ({today})."
        if dry_run:
            log(f"[DRY-RUN] Would send: {msg}")
            return
        ok = send_telegram(msg)
        log(f"nothing-scheduled message: {'sent' if ok else 'FAILED — check TELEGRAM_CHAT_ID secret'}")
        if not ok:
            sys.exit(1)
        return

    for p in batch:
        p["content"] = resolve_edition_links(p.get("content") or "", editions)
        if p.get("first_comment"):
            p["first_comment"] = resolve_edition_links(p["first_comment"], editions)

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
        if dry_run:
            log(f"\n[DRY-RUN] message {i + 1}/{len(queue)} ({len(m)} chars):\n{m}\n{'─'*60}")
            ok = True
        else:
            ok = send_telegram(m)
        sent += ok
        if not dry_run:
            log(f"message {i + 1}/{len(queue)}: {'sent' if ok else 'FAILED'}")
        if not dry_run and i < len(queue) - 1:
            time.sleep(GAP)

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
    log(f"\n{sent}/{len(queue)} messages {'previewed' if dry_run else 'delivered'}.")

    if not dry_run and sent < len(queue):
        sys.exit(1)


if __name__ == "__main__":
    main()
