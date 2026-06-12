#!/usr/bin/env python3
"""
BrainyAct Social Agent - autonomous weekly content runner.

What it does, in order, for each platform:
  1. Reads history.json to find this platform's current rotation week (A/B/C).
  2. Calls the Anthropic API to generate 5 posts for that week's pillars.
  3. For Instagram/Facebook: fetches a relevant stock image from Unsplash (free).
  4. Posts each one to Publer as a DRAFT (state: "draft") with media. Nothing goes live.
  5. Advances the rotation week and logs the run to history.json.
  6. Writes run_summary.md for the GitHub Actions notification step.

It never publishes. Macy reviews drafts in Publer, adds/edits media if needed, and approves.

Local use:
  python generate_and_post.py                 # all platforms, real drafts
  python generate_and_post.py --dry-run       # generate only, no posting
  python generate_and_post.py --platform linkedin
  python generate_and_post.py --platform instagram --platform facebook

Environment variables required:
  ANTHROPIC_API_KEY   your Anthropic API key
  PUBLER_API_KEY      your Publer API key

No API key required for image generation (uses free Unsplash API).
"""

import argparse
import datetime as dt
import json
import os
import sys

import requests
from anthropic import Anthropic

import config

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")
SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "run_summary.md")

# Unsplash free API (no key required, but best effort for rate limiting)
UNSPLASH_API_URL = "https://api.unsplash.com/photos/random"


# ---------------------------------------------------------------------------
# History / rotation state
# ---------------------------------------------------------------------------
def load_history():
    if not os.path.exists(HISTORY_PATH):
        return {"platforms": {}, "runs": []}
    with open(HISTORY_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_history(history):
    with open(HISTORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2)
        fh.write("\n")


def current_week_index(history, platform):
    return history.get("platforms", {}).get(platform, {}).get("week_index", 0)


def advance_week_index(history, platform):
    rotation_len = len(config.PLATFORMS[platform]["rotation"])
    cur = current_week_index(history, platform)
    history.setdefault("platforms", {}).setdefault(platform, {})
    history["platforms"][platform]["week_index"] = (cur + 1) % rotation_len


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate_posts(client, platform, pillars):
    cfg = config.PLATFORMS[platform]
    user_prompt = cfg["user_template"].format(pillars=", ".join(pillars))

    resp = client.messages.create(
        model=cfg["model"],
        max_tokens=config.MAX_TOKENS,
        system=cfg["system_prompt"],
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = "".join(block.text for block in resp.content if block.type == "text")
    cleaned = raw.replace("```json", "").replace("```", "").strip()

    posts = json.loads(cleaned)
    if not isinstance(posts, list) or not posts:
        raise ValueError(f"{platform}: model returned no usable posts")
    return posts


# ---------------------------------------------------------------------------
# Image fetching from Unsplash (free)
# ---------------------------------------------------------------------------
def fetch_image_for_post(platform, post):
    """
    Fetch a relevant stock image from Unsplash (free API, no key required).
    Returns the image URL or None if fetching fails.
    """
    try:
        body = post.get("body", "")
        pillar = post.get("pillar", "post")

        # Use pillar as search query for Unsplash (e.g., "Parent Wins", "How It Works")
        # If pillar is generic, add context based on platform
        search_query = pillar
        if platform == "instagram" and len(search_query) < 3:
            search_query = f"{pillar} neurodiversity children"
        elif platform == "facebook" and len(search_query) < 3:
            search_query = f"{pillar} family parenting"

        params = {
            "query": search_query,
            "w": 1080,  # Instagram optimal width
            "h": 1350,  # Instagram optimal height (9:11 aspect ratio)
            "orientation": "portrait",
        }

        resp = requests.get(UNSPLASH_API_URL, params=params, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            image_url = data.get("urls", {}).get("regular")
            if image_url:
                return image_url
        return None
    except Exception as exc:
        print(f"  WARNING: Unsplash image fetch failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Publer (server-side, so no CORS issue, and the User-Agent header is required)
# ---------------------------------------------------------------------------
def post_to_publer(api_key, platform, text, image_url=None):
    cfg = config.PLATFORMS[platform]
    headers = {
        "Authorization": f"Bearer-API {api_key}",
        "Publer-Workspace-Id": config.PUBLER_WORKSPACE_ID,
        "Content-Type": "application/json",
        "User-Agent": config.PUBLER_USER_AGENT,
    }

    # Build media array only for Instagram and Facebook with fetched images
    media = []
    if image_url and platform in ("instagram", "facebook"):
        media.append({"type": "image", "url": image_url})

    payload = {
        "bulk": {
            "state": "draft",  # never "draft_private" - that silently fails
            "posts": [{
                "networks": {cfg["network"]: {
                    "type": "status",
                    "text": text,
                    "media": media,  # Include media for Instagram/Facebook
                }},
                "accounts": [{"id": cfg["account_id"]}],
            }],
        }
    }
    resp = requests.post(
        config.PUBLER_ENDPOINT, headers=headers, json=payload, timeout=60
    )
    ok = resp.status_code in (200, 201)
    return ok, resp.status_code, resp.text[:300]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_platform(client, publer_key, history, platform, dry_run):
    cfg = config.PLATFORMS[platform]
    week_idx = current_week_index(history, platform)
    week_letter = "ABC"[week_idx % 3]
    pillars = cfg["rotation"][week_idx]

    log = [f"### {cfg['label']} (Week {week_letter})"]
    print(f"\n=== {cfg['label']} | Week {week_letter} | pillars: {pillars} ===")

    try:
        posts = generate_posts(client, platform, pillars)
    except Exception as exc:  # noqa: BLE001 - surface any generation failure
        msg = f"Generation FAILED: {exc}"
        print(msg)
        log.append(f"- {msg}")
        return {"platform": platform, "ok": False, "log": "\n".join(log),
                "sent": 0, "total": 0}

    sent = 0
    for i, post in enumerate(posts, start=1):
        body = post.get("body", "").strip()
        pillar = post.get("pillar", f"post {i}")
        if not body:
            log.append(f"- {pillar}: empty body, skipped")
            continue

        # Fetch image for Instagram/Facebook posts
        image_url = None
        if platform in ("instagram", "facebook") and not dry_run:
            print(f"  [{i}] {pillar}: fetching image from Unsplash...")
            image_url = fetch_image_for_post(platform, post)
            if image_url:
                print(f"       image fetched: {image_url[:60]}...")
            else:
                print(f"       image fetch failed, proceeding without media")

        if dry_run:
            media_status = f" + image" if image_url else ""
            print(f"  [{i}] {pillar} ({len(body)} chars){media_status} - DRY RUN, not posted")
            log.append(f"- {pillar}: generated ({len(body)} chars){media_status}, dry run")
            continue

        ok, status, detail = post_to_publer(publer_key, platform, body, image_url=image_url)
        if ok:
            sent += 1
            media_status = " + image" if image_url else ""
            print(f"  [{i}] {pillar} -> Publer draft OK{media_status}")
            log.append(f"- {pillar}: draft created{media_status}")
        else:
            print(f"  [{i}] {pillar} -> FAILED ({status}) {detail}")
            log.append(f"- {pillar}: FAILED ({status})")

    if not dry_run:
        advance_week_index(history, platform)

    return {"platform": platform, "ok": True, "log": "\n".join(log),
            "sent": sent, "total": len(posts)}


def main():
    parser = argparse.ArgumentParser(description="BrainyAct social agent runner")
    parser.add_argument(
        "--platform", action="append",
        choices=list(config.PLATFORMS.keys()),
        help="Limit to one or more platforms (repeatable). Default: all.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate and print posts without sending to Publer or advancing rotation.",
    )
    args = parser.parse_args()

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    publer_key = os.environ.get("PUBLER_API_KEY")

    if not anthropic_key:
        sys.exit("Missing ANTHROPIC_API_KEY")
    if not publer_key and not args.dry_run:
        sys.exit("Missing PUBLER_API_KEY (or use --dry-run)")

    client = Anthropic(api_key=anthropic_key)
    history = load_history()
    platforms = args.platform or list(config.PLATFORMS.keys())

    results = []
    for platform in platforms:
        results.append(
            run_platform(client, publer_key, history, platform, args.dry_run)
        )

    if not args.dry_run:
        history.setdefault("runs", []).append({
            "date": dt.date.today().isoformat(),
            "results": [{"platform": r["platform"], "sent": r["sent"],
                         "total": r["total"]} for r in results],
        })
        save_history(history)

    write_summary(results, args.dry_run)


def write_summary(results, dry_run):
    today = dt.date.today().isoformat()
    total_sent = sum(r["sent"] for r in results)
    mode = "DRY RUN (nothing posted)" if dry_run else "drafts created in Publer"
    lines = [
        f"# BrainyAct weekly drafts - {today}",
        "",
        f"{total_sent} drafts {('would be created' if dry_run else 'created')} this run ({mode}).",
        "",
        "Open Publer to add images/video and approve drafts for scheduling." if not dry_run else "",
        "",
    ]
    for r in results:
        lines.append(r["log"])
        lines.append("")
    with open(SUMMARY_PATH, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(f"\nSummary written to {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
