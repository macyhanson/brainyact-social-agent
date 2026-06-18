#!/usr/bin/env python3
"""
BrainyAct Social Agent - autonomous content runner.

What it does, in order, for each platform:
  1. Reads history.json for rotation state and recent-angle memory.
  2. Generates posts with the Anthropic API.
       - LinkedIn (evergreen): splits the run across audiences (payors, care
         coordinators, employers) by weight, batched in fives so large runs
         never truncate.
       - LinkedIn (--campaign): single-audience campaign sequence, also batched.
       - Instagram / Facebook: unchanged single call of 5 posts.
  3. For Instagram/Facebook: fetches a relevant stock image from Unsplash (free).
  4. Posts each one to Publer as a DRAFT (state: "draft"). Nothing goes live.
  5. Advances rotation (B2C) and updates recent-angle memory, then logs the run.
  6. Writes run_summary.md for the GitHub Actions notification step.

Freshness: a per-run ledger stops two posts in one run from repeating an angle,
and recent opening lines are remembered across runs in history.json so back-to-
back runs do not repeat themselves.

Local use:
  python generate_and_post.py                          # all platforms, real drafts
  python generate_and_post.py --dry-run                # generate only, no posting
  python generate_and_post.py --platform linkedin
  python generate_and_post.py --platform linkedin --count 30
  python generate_and_post.py --platform linkedin --campaign centene --count 10

Environment variables required:
  ANTHROPIC_API_KEY   your Anthropic API key
  PUBLER_API_KEY      your Publer API key
"""

import argparse
import datetime as dt
import json
import os
import random
import sys

import requests
from anthropic import Anthropic

import config

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "history.json")
SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "run_summary.md")

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


def recent_angles(history, platform):
    return history.get("platforms", {}).get(platform, {}).get("recent_angles", [])


def store_recent_angles(history, platform, ledger):
    history.setdefault("platforms", {}).setdefault(platform, {})
    history["platforms"][platform]["recent_angles"] = ledger[-config.RECENT_ANGLE_MEMORY:]


# ---------------------------------------------------------------------------
# Freshness helpers
# ---------------------------------------------------------------------------
def summarize_angle(post):
    """Compact opening-line signature used to avoid repeats within and across runs."""
    hook = (post.get("hook") or "").strip()
    if not hook:
        hook = (post.get("body") or "").strip().split("\n")[0]
    aud = post.get("audience", "")
    topic = post.get("topic", "")
    tag = f"[{aud}] " if aud else ""
    extra = f" ({topic})" if topic else ""
    return f"{tag}{hook[:90]}{extra}"


def ledger_directive(ledger):
    if not ledger:
        return ""
    recent = ledger[-60:]
    joined = "\n".join(f"- {a}" for a in recent)
    return ("\n\nDo NOT repeat any of these angles or opening lines that were "
            f"used recently. Take a different angle:\n{joined}")


def distribute_counts(weights, total):
    """Split `total` across weighted keys (largest-remainder), always summing to total."""
    keys = list(weights.keys())
    wsum = sum(weights.values()) or 1
    raw = {k: weights[k] / wsum * total for k in keys}
    floored = {k: int(raw[k]) for k in keys}
    remainder = total - sum(floored.values())
    order = sorted(keys, key=lambda k: raw[k] - floored[k], reverse=True)
    for k in order[:remainder]:
        floored[k] += 1
    return floored


# ---------------------------------------------------------------------------
# Model call
# ---------------------------------------------------------------------------
def call_model(client, platform, system_prompt, user_prompt):
    cfg = config.PLATFORMS[platform]
    resp = client.messages.create(
        model=cfg["model"],
        max_tokens=config.MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(cleaned)
    if not isinstance(data, list) or not data:
        raise ValueError("model returned no usable posts")
    return data


def call_model_with_retry(client, platform, system_prompt, user_prompt, attempts=2):
    last = None
    for _ in range(attempts):
        try:
            return call_model(client, platform, system_prompt, user_prompt)
        except Exception as exc:  # noqa: BLE001 - one retry on truncation/parse error
            last = exc
    raise last


# ---------------------------------------------------------------------------
# Generation: Instagram / Facebook (unchanged single call of 5)
# ---------------------------------------------------------------------------
def generate_posts(client, platform, pillars, count, system_prompt):
    cfg = config.PLATFORMS[platform]
    short_n = count // 2
    medium_n = count - short_n
    user_prompt = cfg["user_template"].format(
        pillars=", ".join(pillars), count=count, short_n=short_n, medium_n=medium_n,
    )
    return call_model_with_retry(client, platform, system_prompt, user_prompt)


# ---------------------------------------------------------------------------
# Generation: count-aware template, batched (LinkedIn campaign path)
# ---------------------------------------------------------------------------
def generate_template_batched(client, platform, pillars, count, system_prompt, ledger):
    cfg = config.PLATFORMS[platform]
    posts = []
    for start in range(0, count, config.POSTS_PER_BATCH):
        chunk_pillars = pillars[start:start + config.POSTS_PER_BATCH]
        n = len(chunk_pillars)
        short_n = n // 2
        medium_n = n - short_n
        user_prompt = cfg["user_template"].format(
            pillars=", ".join(chunk_pillars), count=n, short_n=short_n, medium_n=medium_n,
        )
        user_prompt += ledger_directive(ledger)
        batch = call_model_with_retry(client, platform, system_prompt, user_prompt)
        for p in batch:
            posts.append(p)
            ledger.append(summarize_angle(p))
    return posts


# ---------------------------------------------------------------------------
# Generation: LinkedIn multi-audience (evergreen path)
# ---------------------------------------------------------------------------
def build_audience_prompt(aud, chunk_len, length_plan, ledger):
    formats_src = aud.get("formats") or config.LINKEDIN_FORMATS
    hooks_src = aud.get("hook_bank") or config.LINKEDIN_HOOKS
    formats = random.sample(formats_src, k=min(chunk_len, len(formats_src)))
    hooks = random.sample(hooks_src, k=min(chunk_len, len(hooks_src)))
    pillars = aud["pillars"]

    topics_src = aud.get("topics") or []
    topics = random.sample(topics_src, k=min(chunk_len, len(topics_src))) if topics_src else []

    hashtags_on = aud.get("hashtags", True)
    word_short = aud.get("word_short", "150 to 250")
    word_medium = aud.get("word_medium", "300 to 500")
    cta_bank = aud.get("cta_bank")
    cta_strong = aud.get("cta_strong") or []

    tr = aud.get("training", {})
    ex_block = ""
    examples = tr.get("examples", [])
    if examples:
        pick = random.sample(examples, k=min(3, len(examples)))
        joined = "\n\n".join(f'"{e.strip()[:1200]}"' for e in pick)
        ex_block = ("\nImitate the voice, length, and structure of these proven posts "
                    f"(do not copy their wording):\n{joined}\n")

    facts = tr.get("facts", [])
    facts_block = ("\nAudience facts to respect:\n" + "\n".join(f"- {f}" for f in facts)) if facts else ""
    requires = tr.get("requires", [])
    bans = tr.get("bans", [])
    req_line = ("\nEvery post must: " + "; ".join(requires)) if requires else ""
    ban_line = ("\nNo post may use: " + "; ".join(bans)) if bans else ""

    hashtag_rule = ("Include #BrainyAct #Neurodiversity #DigitalTherapeutics plus 2 "
                    "pillar-specific tags." if hashtags_on else "Do not use any hashtags.")

    post_lines = []
    for i in range(chunk_len):
        fmt = formats[i % len(formats)]
        hook = hooks[i % len(hooks)]
        length = length_plan[i]
        words = word_short if length == "short" else word_medium
        if cta_bank:
            if cta_strong and random.random() < 0.2:
                cta = random.choice(cta_strong)
            else:
                cta = random.choice(cta_bank)
        else:
            cta = aud["cta"]
        lines = [
            f"Post {i + 1}",
            f"  Pillar: {pillars[i % len(pillars)]}",
            f"  Format: {fmt['name']} - {fmt['guide']}",
            f"  Hook style: {hook}",
            f"  Length: {length} ({words} words)",
            f"  CTA to end on: {cta}",
            f"  Hashtags: {hashtag_rule}",
            f"  numericPolicy: {aud['numeric_policy']}",
        ]
        if topics:
            lines.insert(2, f"  Suggested angle: {topics[i % len(topics)]}")
        post_lines.append("\n".join(lines))
    body = "\n\n".join(post_lines)

    return (
        f"Generate exactly {chunk_len} LinkedIn posts for this audience: {aud['label']}.\n"
        f"Who they are: {aud['who']}\n"
        f"Their pains: {aud['pains']}\n"
        f"Value props to draw from: {aud['value_props']}\n"
        f"Voice: {aud['language']}"
        f"{ex_block}{facts_block}{req_line}{ban_line}\n\n"
        f"Each post must be structurally different from the others and from anything "
        f"in the do-not-repeat list.\n\n"
        f"{body}"
        f"{ledger_directive(ledger)}\n\n"
        f"Return a JSON array with exactly {chunk_len} objects, each with these fields:\n"
        f'{{"audience": "{aud["label"]}", "pillar": "pillar name", "format": "format name", '
        f'"length": "short or medium", "topic": "5 to 8 word angle summary", '
        f'"hook": "first line", "body": "full post text including hook, body, CTA, and hashtags if used"}}'
    )


def generate_with_audiences(client, platform, count, ledger):
    cfg = config.PLATFORMS[platform]
    audiences = cfg["audiences"]
    weights = cfg["audience_weights"]
    per = distribute_counts(weights, count)
    base_system = cfg["system_prompt"]
    all_posts = []

    for akey, n in per.items():
        if n <= 0:
            continue
        aud = audiences[akey]
        system_prompt = base_system + aud.get("system_addendum", "")
        for start in range(0, n, config.POSTS_PER_BATCH):
            chunk_len = min(config.POSTS_PER_BATCH, n - start)
            # ~40% short, rest medium, per chunk
            length_plan = ["short" if i % 5 < 2 else "medium" for i in range(chunk_len)]
            user_prompt = build_audience_prompt(aud, chunk_len, length_plan, ledger)
            batch = call_model_with_retry(client, platform, system_prompt, user_prompt)
            for p in batch:
                p["audience"] = aud["label"]
                all_posts.append(p)
                ledger.append(summarize_angle(p))

    random.shuffle(all_posts)  # interleave audiences in the Publer draft queue
    return all_posts


# ---------------------------------------------------------------------------
# Image fetching from Unsplash (free) - Instagram / Facebook only
# ---------------------------------------------------------------------------
def fetch_image_for_post(platform, post):
    try:
        pillar = post.get("pillar", "post")
        search_query = pillar
        if platform == "instagram" and len(search_query) < 3:
            search_query = f"{pillar} neurodiversity children"
        elif platform == "facebook" and len(search_query) < 3:
            search_query = f"{pillar} family parenting"

        params = {"query": search_query, "w": 1080, "h": 1350, "orientation": "portrait"}
        resp = requests.get(UNSPLASH_API_URL, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("urls", {}).get("regular")
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"  WARNING: Unsplash image fetch failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Publer (server-side; User-Agent header required for Cloudflare)
# ---------------------------------------------------------------------------
def post_to_publer(api_key, platform, text, image_url=None):
    cfg = config.PLATFORMS[platform]
    headers = {
        "Authorization": f"Bearer-API {api_key}",
        "Publer-Workspace-Id": config.PUBLER_WORKSPACE_ID,
        "Content-Type": "application/json",
        "User-Agent": config.PUBLER_USER_AGENT,
    }
    media = []
    if image_url and platform in ("instagram", "facebook"):
        media.append({"type": "image", "url": image_url})

    payload = {
        "bulk": {
            "state": "draft",  # never "draft_private" - that silently fails
            "posts": [{
                "networks": {cfg["network"]: {"type": "status", "text": text, "media": media}},
                "accounts": [{"id": cfg["account_id"]}],
            }],
        }
    }
    resp = requests.post(config.PUBLER_ENDPOINT, headers=headers, json=payload, timeout=60)
    ok = resp.status_code in (200, 201)
    return ok, resp.status_code, resp.text[:300]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_platform(client, publer_key, history, platform, dry_run, count, campaign_key=None):
    cfg = config.PLATFORMS[platform]
    campaign = config.CAMPAIGNS.get(campaign_key) if campaign_key else None
    campaign_active = bool(campaign and campaign.get("platform") == platform)

    ledger = list(recent_angles(history, platform))  # seed with cross-run memory
    uses_ledger = False

    def fit(pillars):
        if count <= len(pillars):
            return pillars[:count]
        return (pillars * ((count // len(pillars)) + 1))[:count]

    if campaign_active:
        pillars = fit(list(campaign["pillars"]))
        system_prompt = cfg["system_prompt"] + campaign.get("system_addendum", "")
        mode_label = f"Campaign: {campaign['label']}"
        generate = lambda: generate_template_batched(  # noqa: E731
            client, platform, pillars, count, system_prompt, ledger)
        advance = False
        uses_ledger = True
    elif cfg.get("audiences"):
        mode_label = "Multi-audience"
        generate = lambda: generate_with_audiences(client, platform, count, ledger)  # noqa: E731
        advance = False  # LinkedIn freshness comes from audiences + ledger, not week rotation
        uses_ledger = True
    else:
        week_idx = current_week_index(history, platform)
        week_letter = "ABC"[week_idx % 3]
        pillars = fit(list(cfg["rotation"][week_idx]))
        system_prompt = cfg["system_prompt"]
        mode_label = f"Week {week_letter}"
        generate = lambda: generate_posts(client, platform, pillars, count, system_prompt)  # noqa: E731
        advance = not dry_run

    log = [f"### {cfg['label']} ({mode_label})"]
    print(f"\n=== {cfg['label']} | {mode_label} | {count} posts ===")

    try:
        posts = generate()
    except Exception as exc:  # noqa: BLE001 - surface any generation failure
        msg = f"Generation FAILED: {exc}"
        print(msg)
        log.append(f"- {msg}")
        return {"platform": platform, "ok": False, "log": "\n".join(log), "sent": 0, "total": 0}

    sent = 0
    for i, post in enumerate(posts, start=1):
        body = (post.get("body") or "").strip()
        pillar = post.get("pillar", f"post {i}")
        aud = post.get("audience")
        tag = f"{aud} | {pillar}" if aud else pillar
        if not body:
            log.append(f"- {tag}: empty body, skipped")
            continue

        image_url = None
        if platform in ("instagram", "facebook") and not dry_run:
            print(f"  [{i}] {tag}: fetching image from Unsplash...")
            image_url = fetch_image_for_post(platform, post)
            print(f"       {'image fetched' if image_url else 'no image, proceeding'}")

        if dry_run:
            media_status = " + image" if image_url else ""
            print(f"  [{i}] {tag} ({len(body)} chars){media_status} - DRY RUN, not posted")
            log.append(f"- {tag}: generated ({len(body)} chars){media_status}, dry run")
            continue

        ok, status, detail = post_to_publer(publer_key, platform, body, image_url=image_url)
        if ok:
            sent += 1
            media_status = " + image" if image_url else ""
            print(f"  [{i}] {tag} -> Publer draft OK{media_status}")
            log.append(f"- {tag}: draft created{media_status}")
        else:
            print(f"  [{i}] {tag} -> FAILED ({status}) {detail}")
            log.append(f"- {tag}: FAILED ({status})")

    if advance:
        advance_week_index(history, platform)
    if uses_ledger and not dry_run:
        store_recent_angles(history, platform, ledger)

    return {"platform": platform, "ok": True, "log": "\n".join(log),
            "sent": sent, "total": len(posts)}


def main():
    parser = argparse.ArgumentParser(description="BrainyAct social agent runner")
    parser.add_argument("--platform", action="append", choices=list(config.PLATFORMS.keys()),
                        help="Limit to one or more platforms (repeatable). Default: all.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate and print posts without sending to Publer or advancing state.")
    parser.add_argument("--count", type=int, default=None,
                        help=f"Posts to generate per platform (default: {config.POSTS_PER_RUN}).")
    parser.add_argument("--campaign", default=None, choices=list(config.CAMPAIGNS.keys()),
                        help="Apply a campaign overlay (e.g. centene). Bypasses the audience split.")
    args = parser.parse_args()

    count = args.count if args.count is not None else config.POSTS_PER_RUN
    if count < 1:
        sys.exit("--count must be at least 1")

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
            run_platform(client, publer_key, history, platform, args.dry_run,
                         count, campaign_key=args.campaign)
        )

    if not args.dry_run:
        history.setdefault("runs", []).append({
            "date": dt.date.today().isoformat(),
            "results": [{"platform": r["platform"], "sent": r["sent"], "total": r["total"]}
                        for r in results],
        })
        save_history(history)

    write_summary(results, args.dry_run)


def write_summary(results, dry_run):
    today = dt.date.today().isoformat()
    total_sent = sum(r["sent"] for r in results)
    mode = "DRY RUN (nothing posted)" if dry_run else "drafts created in Publer"
    lines = [
        f"# BrainyAct drafts - {today}",
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
