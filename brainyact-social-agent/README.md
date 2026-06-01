# BrainyAct Social Agent

Autonomous weekly content generator for BrainyAct by Kinuu. It generates a week
of posts for LinkedIn, Instagram, and Facebook, pushes them to Publer as
**drafts**, and opens a GitHub issue so you know they are ready. It never
publishes. You review in Publer, add media, and approve.

B2B and B2C run on separate days: LinkedIn posts Tuesday morning, Instagram and
Facebook post Thursday morning. Each is its own workflow file, so you can move
either day without touching the other.

Total running cost is about a dollar a month in Anthropic API tokens. GitHub
Actions and Publer add nothing beyond what you already pay.

## What it produces each week

- LinkedIn: 5 B2B posts (payors, employers, clinical buyers), generated on Sonnet
- Instagram: 3 Reels captions + 2 static captions (parents/families), on Haiku
- Facebook: 5 B2C posts (parents/families), on Haiku

Pillars rotate on a 3-week A/B/C cycle per platform so coverage stays even. The
cycle position is stored in `history.json` and advances automatically after each
successful run.

## One-time setup

1. Create a private GitHub repo and add every file in this folder, keeping the
   `.github/workflows/` path intact.

2. Add two repository secrets under Settings > Secrets and variables > Actions:
   - `ANTHROPIC_API_KEY`
   - `PUBLER_API_KEY` (value: `d24877bf9684eed77b02d900cc589b0bf70bd3f6fcc54fc0`)

   Account IDs and the workspace ID are not secrets and live in `config.py`.

3. That is it. Two workflows run on their own schedules:
   - "B2B content (LinkedIn)" every Tuesday at 13:00 UTC (8:00 AM Central)
   - "B2C content (Instagram + Facebook)" every Thursday at 13:00 UTC

   To run either now, open the Actions tab, pick the workflow, and click "Run
   workflow." Check the dry-run box first if you want to see the posts without
   sending anything to Publer.

## Local testing (optional)

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in your keys
export $(grep -v '^#' .env | xargs)

python generate_and_post.py --dry-run               # generate, print, post nothing
python generate_and_post.py --platform linkedin     # one platform, real drafts
python generate_and_post.py                          # all three, real drafts
```

A dry run never posts and never advances the rotation, so you can run it freely.

## How the schedule and notification work

Two workflow files drive everything. `.github/workflows/b2b-linkedin.yml` fires
on `0 13 * * 2` (Tuesday) and runs LinkedIn only.
`.github/workflows/b2c-social.yml` fires on `0 13 * * 4` (Thursday) and runs
Instagram and Facebook. Each one commits the updated `history.json`, writes a
summary into the Actions log, and opens its own review issue using the built-in
token, which sends you a GitHub email. No SMTP setup needed.

Both share a `concurrency: group: social-agent` lock so they can never write
`history.json` at the same time, and each rebases before pushing as a second
safeguard. To change a posting day, edit the cron line in that one file.

## Editing content

Everything you would tune lives in `config.py`: pillars, system prompts, user
prompts, the A/B/C rotations, which model each platform uses, and post counts.
The runner in `generate_and_post.py` stays generic, so you rarely touch it.

To change posting day or time, edit the cron expression. To move drafts to a
different Publer account, change the `account_id` for that platform in
`config.py`.

## Guardrails built in

- Posts are created with `state: "draft"` only. Nothing goes live without you.
- Every Publer call sends the browser User-Agent header Cloudflare requires.
- Brand rules (no em dashes, no competitor names, ABA-complement positioning,
  outcome-language compliance, mandatory CTA and hashtags) are enforced in the
  system prompts.
- A generation failure on one platform does not stop the others.
