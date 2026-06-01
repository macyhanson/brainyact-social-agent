#!/usr/bin/env python3
"""
BrainyAct Social Agent - autonomous weekly content runner.

What it does, in order, for each platform:
  1. Reads history.json to find this platform's current rotation week (A/B/C).
  2. Calls the Anthropic API to generate 5 posts for that week's pillars.
  3. Posts each one to Publer as a DRAFT (state: "draft"). Nothing goes live.
  4. Advances the rotation week and logs the run to history.json.
  5. Writes run_summary.md for the GitHub Actions notification step.

It never publishes. Macy reviews drafts in Publer, adds media, and approves.

Local use:
  python generate_and_post.py                 # all platforms, real drafts
  python generate_and_post.py --dry-run       # generate only, no posting
  python generate_and_post.py --platform linkedin
  python generate_and_post.py --platform instagram --platform facebook

Environment variables required:
  ANTHROPIC_API_KEY   your Anthropic API key
  PUBLER_API_KEY      your Publer API key
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
# Publer (server-side, so no CORS issue, and the User-Agent header is required)
# ---------------------------------------------------------------------------
def post_to_publer(api_key, platform, text):
    cfg = config.PLATFORMS[platform]
    headers = {
        "Authorization": f"Bearer-API {api_key}",
        "Publer-Workspace-Id": config.PUBLER_WORKSPACE_ID,
        "Content-Type": "application/json",
        "User-Agent": config.PUBLER_USER_AGENT,
    }
    payload = {
        "bulk": {
            "state": "draft",  # never "draft_private" - that silently fails
            "posts": [{
                "networks": {cfg["network"]: {"type": "status", "text": text}},
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

        if dry_run:
            print(f"  [{i}] {pillar} ({len(body)} chars) - DRY RUN, not posted")
            log.append(f"- {pillar}: generated ({len(body)} chars), dry run")
            continue

        ok, status, detail = post_to_publer(publer_key, platform, body)
        if ok:
            sent += 1
            print(f"  [{i}] {pillar} -> Publer draft OK")
            log.append(f"- {pillar}: draft created")
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
        "Open Publer to add images/video and approve drafts for scheduling.",
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
