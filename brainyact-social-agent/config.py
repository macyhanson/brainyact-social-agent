"""
BrainyAct Social Agent - platform configuration.

Everything platform-specific lives here so the runner (generate_and_post.py)
stays generic. Edit pillars, prompts, rotations, and model choices in this file.

Ported directly from the three Claude skills:
  - linkedin-b2b-agent
  - instagram-agent
  - b2c-social-agent

Publer credentials and the Anthropic key are NOT stored here. They come from
environment variables (GitHub Actions secrets). See README.md.
"""

# ---------------------------------------------------------------------------
# Publer routing (account IDs are not secrets, the API key is)
# ---------------------------------------------------------------------------
PUBLER_WORKSPACE_ID = "680fe03e02cf6a3063e9468e"
PUBLER_ENDPOINT = "https://app.publer.io/api/v1/posts/schedule"

# Cloudflare blocks requests with no browser User-Agent (403, error 1010).
PUBLER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# Model strings. LinkedIn copy goes to payors and clinical buyers, so it runs
# on Sonnet for sharper writing. B2C runs on Haiku to keep cost near zero.
MODEL_SONNET = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"

POSTS_PER_RUN = 5
MAX_TOKENS = 8000  # lower values truncate the JSON across 5 full posts


# ---------------------------------------------------------------------------
# LinkedIn (B2B: payors, self-insured employers, clinical decision-makers)
# ---------------------------------------------------------------------------
LINKEDIN_SYSTEM = """You are a B2B LinkedIn content strategist for Kinuu, the company behind BrainyAct, a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Your audience: insurance payors, self-insured employers, HR benefits leaders, clinical directors, and healthcare decision-makers.

Brand rules:
- Always include a CTA referencing brainyact.com
- Never name competitors
- No em dashes
- No generic AI opener phrases like "In today's landscape"
- Mix clinical credibility with conversational voice
- Hashtags: always include #BrainyAct #Neurodiversity #DigitalTherapeutics plus 2 pillar-specific tags
- BrainyAct is positioned as a complement to ABA therapy, not a replacement
- Reference the 473-user outcomes dataset when relevant
- Company is Kinuu, LLC

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

LINKEDIN_USER_TEMPLATE = """Generate 5 LinkedIn posts for this week. Use these pillars in this order: {pillars}. Vary the length: include 2 short posts (150 to 250 words) and 3 medium posts (300 to 500 words). Each post must feel distinct in structure and tone from the others.

Return a JSON array with exactly 5 objects, each with these fields:
{{
  "pillar": "pillar name",
  "length": "short or medium",
  "hook": "first line of the post",
  "body": "full post text including hook, body, CTA, and hashtags"
}}"""

# ---------------------------------------------------------------------------
# Instagram (B2C: parents, caregivers, families) - 3 Reels + 2 static
# ---------------------------------------------------------------------------
INSTAGRAM_SYSTEM = """You are an Instagram content strategist for Kinuu, the company behind BrainyAct, a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Audience: parents, caregivers, and families of children and young adults with neurodevelopmental conditions.

Brand rules:
- Tone: warm, hopeful, relatable, the voice of a knowledgeable friend, never clinical or corporate
- Always include a CTA referencing brainyact.com or "book a free consultation at brainyact.com"
- Never name competitors
- No em dashes
- No generic AI opener phrases like "In today's world" or "As parents, we all know"
- Hashtags: always include #BrainyAct plus 4 to 6 condition/topic-relevant tags
- BrainyAct complements OT and ABA, never frames against them
- Language: "many families report," "shown to," "participants demonstrated", never "cures" or "treats"
- Age range: 6 to 30. Do not reference toddlers or infants.
- Outcome disclaimer when citing data: "Results based on aggregated data from BrainyAct program participants. Individual outcomes vary."

Reels captions (format: "reel"): Hook-driven first line, fast conversational pace, 80 to 150 words total. Written to accompany a video.
Static captions (format: "static"): Story or education arc, 150 to 250 words. Designed to be read standalone.

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

INSTAGRAM_USER_TEMPLATE = """Generate 5 Instagram posts. First 3 are Reels captions (format: "reel"), last 2 are static post captions (format: "static").

Use these pillars in this order: {pillars}.

Each post must feel distinct in hook style and tone: vary between emotional/parent-relatable, science/mechanism, and transformation/outcome formats.

Return a JSON array with exactly 5 objects:
{{
  "pillar": "pillar name",
  "format": "reel or static",
  "hook": "first line of the post",
  "body": "full post text including hook, body, CTA, and hashtags"
}}"""

# ---------------------------------------------------------------------------
# Facebook (B2C: parents, caregivers, families)
# ---------------------------------------------------------------------------
FACEBOOK_SYSTEM = """You are a B2C social media content strategist for Kinuu, the company behind BrainyAct, a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Your audience: parents, caregivers, and families of children and young adults with neurodevelopmental conditions.

Brand rules:
- Tone: warm, hopeful, relatable, the voice of a knowledgeable friend, never clinical or corporate
- Always include a CTA referencing brainyact.com or "book a free consultation at brainyact.com"
- Never name competitors
- No em dashes
- No generic AI opener phrases like "In today's world" or "As parents, we all know"
- Hashtags: always include #BrainyAct plus 4 to 6 condition/topic-relevant tags
- BrainyAct complements OT and ABA, never frames against them
- Language: "many families report," "shown to," "participants demonstrated", never "cures" or "treats"
- Age range: 6 to 30. Do not reference toddlers or infants.
- Outcome disclaimer when citing data: "Results based on aggregated data from BrainyAct program participants. Individual outcomes vary."

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

FACEBOOK_USER_TEMPLATE = """Generate 5 Facebook posts for this week. Use these pillars in this order: {pillars}. Vary the length: include 2 short posts (80 to 130 words) and 3 medium posts (150 to 250 words). Each post must feel distinct in hook style and tone: vary between emotional/parent-relatable, science/mechanism, and transformation/outcome formats.

Return a JSON array with exactly 5 objects, each with these fields:
{{
  "pillar": "pillar name",
  "length": "short or medium",
  "hook": "first line of the post",
  "body": "full post text including hook, body, CTA, and hashtags"
}}"""


# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------
# Each platform defines its Publer network key, account id, model, prompts, and
# a 3-week pillar rotation (A / B / C). The runner advances the week index per
# platform every successful run so coverage stays even.
PLATFORMS = {
    "linkedin": {
        "label": "LinkedIn",
        "network": "linkedin",
        "account_id": "68360d90c7a351d4c0097a84",
        "model": MODEL_SONNET,
        "system_prompt": LINKEDIN_SYSTEM,
        "user_template": LINKEDIN_USER_TEMPLATE,
        "rotation": [
            ["Payor ROI", "Clinical Outcomes", "Employer Benefits",
             "Neurodiversity Awareness", "BrainyAct Product"],
            ["Clinical Outcomes", "Employer Benefits", "Neurodiversity Awareness",
             "Thought Leadership", "Payor ROI"],
            ["Employer Benefits", "Thought Leadership", "BrainyAct Product",
             "Payor ROI", "Clinical Outcomes"],
        ],
    },
    "instagram": {
        "label": "Instagram",
        "network": "instagram",
        "account_id": "680fe0a353e7e3779c8e2cd4",
        "model": MODEL_HAIKU,
        "system_prompt": INSTAGRAM_SYSTEM,
        "user_template": INSTAGRAM_USER_TEMPLATE,
        "rotation": [
            ["How It Works", "Parent Wins", "Understanding Your Child",
             "BrainyAct Platform", "Condition Spotlight"],
            ["Parent Wins", "Science Made Simple", "BrainyAct Platform",
             "How It Works", "Understanding Your Child"],
            ["Condition Spotlight", "How It Works", "Science Made Simple",
             "Parent Wins", "BrainyAct Platform"],
        ],
    },
    "facebook": {
        "label": "Facebook",
        "network": "facebook",
        "account_id": "680fe08253e7e3779c8e2cb1",
        "model": MODEL_HAIKU,
        "system_prompt": FACEBOOK_SYSTEM,
        "user_template": FACEBOOK_USER_TEMPLATE,
        "rotation": [
            ["How It Works", "Parent Wins", "Understanding Your Child",
             "BrainyAct Platform", "Condition Spotlight"],
            ["Parent Wins", "Science Made Simple", "BrainyAct Platform",
             "How It Works", "Understanding Your Child"],
            ["Condition Spotlight", "How It Works", "Science Made Simple",
             "Parent Wins", "BrainyAct Platform"],
        ],
    },
}
