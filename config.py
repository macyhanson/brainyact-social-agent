"""
BrainyAct Social Agent - platform configuration.

Everything platform-specific lives here so the runner (generate_and_post.py)
stays generic. Edit pillars, prompts, rotations, audiences, and model choices
in this file.

Ported directly from the three Claude skills:
  - linkedin-b2b-agent  (now multi-audience: payors / care coordinators / employers)
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
MAX_TOKENS = 8000        # lower values truncate the JSON across ~5 full posts
POSTS_PER_BATCH = 5      # never ask the model for more than this in one call
RECENT_ANGLE_MEMORY = 40  # how many recent opening lines to remember per platform


# ---------------------------------------------------------------------------
# brainyact.com grounding (refresh when the site changes)
# ---------------------------------------------------------------------------
SITE_FACTS = """BrainyAct by Kinuu. Tagline: "Putting Hope in Motion." Brand line: "Transformation, not just treatment."
Reimagined developmental care with progress framed over a 6-month horizon, zero wait time, personalized programs. Ages 6+, with or without a formal diagnosis.
Conditions: autism spectrum, ADHD, sensory processing disorder, dyslexia, dyscalculia, dysgraphia, adoption trauma, anxiety.
Supporting skill areas: communication, focus and concentration, handwriting, motor coordination, self-confidence, social skills, self-regulation, thinking and memory.
Bottom-up developmental model grounded in functional neurology. Complement to ABA, not a replacement.
Health plan value: fewer crisis-driven encounters, less reliance on restrictive environments, improved daily functioning for members and families, utilization data visibility, reduced reliance on prolonged high-intensity services.
Self-insurer value: earlier functional gains without years of services, reduced disruption for working caregivers, predictable program structure, family stability, clear reporting for benefits oversight.
Pages: brainyact.com/the-science, brainyact.com/for-businesses."""


# ---------------------------------------------------------------------------
# Shared B2C parent audience profile
# ---------------------------------------------------------------------------
# Facebook and Instagram both write to the same parent/caregiver consumer, so
# the audience reality and the B2C-specific rules live here once and are spliced
# into both system prompts below. LinkedIn (B2B) does NOT use this.
B2C_AUDIENCE_REALITY = """
Who you are writing to (write from this reality, never state it back at them):
- They carry chronic, low-grade stress and grief that resurfaces at each milestone. They are tired and still trying. Hope and exhaustion coexist. Acknowledge the daily reality before any product feature.
- They are skeptical from past disappointment with programs that overpromised and underdelivered. Earn trust with specific, modest, evidence-backed claims, never hype or enthusiasm.
- Time is their scarcest resource. Make clear BrainyAct fits into an already full life and does not add another task the parent has to facilitate.
- They want their child to feel capable, not broken. Never frame the child as behind, deficient, or needing to be fixed. Meet the child where they are and build from there. Treat the child with dignity.
- They are scientifically literate out of necessity. Explain the science in plain language without condescending or oversimplifying.
- Concrete beats broad. A single small moment that goes differently (a smoother morning, one homework session without a meltdown, an easier transition) lands harder than a statistic about improved outcomes.
- The 6 to 30 age range is a relief, not just a feature: one platform that grows with their child instead of starting over every few years.
"""

B2C_EXTRA_RULES = """- Empathy before features: open on the lived daily reality, not the product. The parent must feel seen before they will read a feature.
- Dignity for the child: never frame the child as broken, behind, deficient, or a problem to manage.
- Address the "one more thing" objection where it fits: signal that BrainyAct slots into a full life and runs largely without the parent facilitating every session.
- Specific over sweeping: prefer one concrete small moment over a broad outcome claim. Skepticism in this audience is high, and specificity is what reads as honest.
"""

# Appended to both B2C user templates to force concrete, empathy-led hooks.
B2C_HOOK_DIRECTIVE = " At least two posts must open on a single concrete daily moment (a smoother morning, one homework session without a meltdown, an easier transition) rather than a broad claim. Lead with empathy before any feature. Never frame the child as broken or behind."


# ---------------------------------------------------------------------------
# LinkedIn (B2B) system prompt - shared base for every audience
# ---------------------------------------------------------------------------
LINKEDIN_SYSTEM = """You are a B2B LinkedIn content strategist for BrainyAct by Kinuu, a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Grounding facts (use these, do not contradict them):
""" + SITE_FACTS + """

The audience for each post is specified in the request: insurance payors and health plans, waiver care coordinators and case managers, or self-insured employers. Write to the audience named in the request.

Brand rules:
- Always include a CTA referencing brainyact.com (the exact framing is assigned per post)
- Never name competitors
- No em dashes
- No generic AI opener phrases like "In today's landscape"
- Mix clinical credibility with conversational voice
- Hashtags: always include #BrainyAct #Neurodiversity #DigitalTherapeutics plus 2 pillar-specific tags
- BrainyAct is positioned as a complement to ABA therapy, not a replacement
- Refer to the company only as "Kinuu" or the product as "BrainyAct by Kinuu". Never write "Kinuu Inc." or "Kinuu, LLC".

Claims integrity (strict):
- Default to qualitative outcomes. Obey each post's numericPolicy exactly.
- Never cite the 473-user dataset, participant counts, or internal numeric outcome statistics as effectiveness evidence. Do not invent numbers. Any external statistic must be a well-established, directional public fact.
- Avoid "proven", "rewire", "cure", and "treatment" used as a medical efficacy claim.

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

# Template kept for the campaign path (single-audience, count-aware, now batched).
LINKEDIN_USER_TEMPLATE = """Generate {count} LinkedIn posts. Use these pillars in this order: {pillars}. Vary the length: include {short_n} short posts (150 to 250 words) and {medium_n} medium posts (300 to 500 words). Each post must feel distinct in structure and tone from the others.

Return a JSON array with exactly {count} objects, each with these fields:
{{
  "pillar": "pillar name",
  "length": "short or medium",
  "topic": "5 to 8 word summary of the angle",
  "hook": "first line of the post",
  "body": "full post text including hook, body, CTA, and hashtags"
}}"""


# ---------------------------------------------------------------------------
# LinkedIn audiences (evergreen multi-audience path)
# ---------------------------------------------------------------------------
# Each LinkedIn run is split across these audiences by weight. Weights scale to
# whatever --count is requested, so a 5-post scheduled run and a 30-post manual
# run both stay balanced. To add an audience: add it here and to the weights.
LINKEDIN_AUDIENCE_WEIGHTS = {"payors": 12, "careCoordinators": 9, "employers": 9}

# Post-shape variety. Pillars set the topic; these set the structure.
LINKEDIN_FORMATS = [
    {"name": "Contrarian take", "guide": "Name a belief the audience holds, then flip it and defend the flip."},
    {"name": "Mini case story", "guide": "One short anonymized narrative of a single family or organizational situation. No names, counts, or stats."},
    {"name": "Numbered framework", "guide": "A tight numbered list of 3 to 4 items, each one or two sentences."},
    {"name": "Question-led", "guide": "Open with a sharp question the audience is actually asking and answer it across the post."},
    {"name": "Reframe", "guide": "Reframe a familiar concept, e.g. 'Engagement isn't a perk, it's the mechanism.'"},
    {"name": "First-person clinical POV", "guide": "Expert thinking out loud using OT and functional-neurology framing (bottom-up, sensorimotor)."},
    {"name": "Myth-bust", "guide": "Name a specific misconception, then dismantle it with reasoning."},
    {"name": "Direct provocation", "guide": "Short and punchy. One bold challenge to the status quo, then a crisp reason it matters."},
    {"name": "Trend read", "guide": "Take a current access or coverage trend and draw a practical implication for this audience."},
]

LINKEDIN_HOOKS = [
    "A bold one-line claim",
    "A surprising but well-established external fact",
    "A specific question",
    "A short scene or moment, one or two lines",
    "A misconception stated flatly, then flipped",
    "A list promise, e.g. 'Three reasons...'",
    "A blunt cost-or-time observation",
]

# numericPolicy is intentionally qualitative for all three audiences. The site
# shows percentages, but payor-facing claims should not, and a methodology
# challenge on unvalidated numbers undercuts the controlled-trial strategy.
_QUALITATIVE = "QUALITATIVE ONLY. No percentages, no participant counts, no site statistics."

LINKEDIN_AUDIENCES = {
    "payors": {
        "label": "Insurance Payors / Health Plans",
        "who": "Medical directors, utilization and care management leaders, and behavioral health policy owners at health plans and Medicaid managed care organizations.",
        "pains": "Prolonged high-intensity service spend, crisis-driven encounters, restrictive placements, limited utilization visibility, and pressure on total cost of care and HEDIS measures.",
        "value_props": "Fewer crisis-driven encounters, less reliance on restrictive environments, improved daily functioning for members and families, utilization data visibility, and reduced reliance on prolonged high-intensity services.",
        "language": "Total cost of care, utilization, member outcomes, medical policy, ED diversion, HEDIS, evidence threshold. Measured, credible, never hyped.",
        "pillars": ["Payor ROI", "Thought Leadership", "Clinical Outcomes", "Neurodiversity Awareness"],
        "cta": "Read the payor brief at brainyact.com/for-businesses, or book a call at brainyact.com.",
        "numeric_policy": _QUALITATIVE,
        "system_addendum": "\n\nWrite for a payor evaluating a vendor. Tone is measured, evidence-aware, and economic. Lead with member outcomes and total cost of care, not enthusiasm.",
        "training": {
            "examples": [],  # paste 2-5 of Macy's best payor posts here as strings
            "facts": ["Internal pre/post data does not meet payor evidence standards; a controlled efficacy trial is in progress. Speak to outcomes qualitatively."],
            "requires": ["Frame around total cost of care and member outcomes"],
            "bans": ["Percentages or participant counts", "'proven', 'rewire', 'cure'", "Competitor names"],
        },
    },
    "careCoordinators": {
        "label": "Care Coordinators / Case Managers",
        "who": "Waiver case managers, support coordinators, and care navigators who route families to services and manage caseloads.",
        "pains": "Long waitlists, hard-to-navigate waiver structures, families churning through services without functional gains, heavy documentation, and few tools that make a referral easy.",
        "value_props": "A program families can start with zero wait time, visible functional progress at home, clear reporting that supports their documentation, and an option that complements existing supports.",
        "language": "Person-centered, waiver and support-plan vocabulary, member and family outcomes, ease of referral, reducing caseload friction. Warm but practical.",
        "pillars": ["Clinical Outcomes", "BrainyAct Product", "Neurodiversity Awareness", "Thought Leadership"],
        "cta": "See how referrals work at brainyact.com/for-businesses, or reach out at brainyact.com.",
        "numeric_policy": _QUALITATIVE,
        "system_addendum": "\n\nWrite for a non-clinical coordinator managing a heavy caseload. Emphasize zero wait time, ease of referral, and progress families see at home. Avoid dense clinical jargon.",
        "training": {
            "examples": [],  # paste 2-5 of Macy's best care-coordinator posts here
            "facts": ["Zero wait time is a real differentiator for coordinators managing waitlists.", "Position as a complement to existing waiver supports, never a replacement."],
            "requires": ["Make the referral path or family benefit concrete"],
            "bans": ["Percentages or participant counts", "Jargon that alienates non-clinical readers"],
        },
    },
    "employers": {
        "label": "Self-Insured Employers",
        "who": "Benefits leaders, total rewards, and HR decision-makers at self-insured employers carrying dependent neurodevelopmental care.",
        "pains": "Rising dependent-care cost, caregiver absenteeism and lost productivity, undifferentiated benefits, unpredictable program structures, and weak reporting.",
        "value_props": "Earlier functional gains without years of services, reduced disruption for working caregivers, predictable program structure, family stability, and clear reporting for benefits oversight.",
        "language": "Benefits differentiation, caregiver productivity, predictable cost, ROI, family stability. Business-first and plain.",
        "pillars": ["Employer Benefits", "Payor ROI", "Neurodiversity Awareness", "Thought Leadership"],
        "cta": "See the employer overview at brainyact.com/for-businesses, or book a call at brainyact.com.",
        "numeric_policy": _QUALITATIVE,
        "system_addendum": "\n\nWrite for a benefits leader weighing cost and differentiation. Lead with caregiver productivity, predictable structure, and family stability.",
        "training": {
            "examples": [],  # paste 2-5 of Macy's best employer posts here
            "facts": ["Caregiver productivity and predictable program structure are the strongest employer hooks."],
            "requires": ["Business-first framing", "Tie to benefits differentiation"],
            "bans": ["'proven', 'rewire', 'cure'", "Internal participant counts"],
        },
    },
}


# ---------------------------------------------------------------------------
# Instagram (B2C: parents, caregivers, families) - 3 Reels + 2 static
# ---------------------------------------------------------------------------
INSTAGRAM_SYSTEM = """You are an Instagram content strategist for Kinuu, the company behind BrainyAct, a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Audience: parents, caregivers, and families of children and young adults with neurodevelopmental conditions.
""" + B2C_AUDIENCE_REALITY + """
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
""" + B2C_EXTRA_RULES + """
Reels captions (format: "reel"): Hook-driven first line, fast conversational pace, 80 to 150 words total. Written to accompany a video.
Static captions (format: "static"): Story or education arc, 150 to 250 words. Designed to be read standalone.

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

INSTAGRAM_USER_TEMPLATE = """Generate 5 Instagram posts. First 3 are Reels captions (format: "reel"), last 2 are static post captions (format: "static").

Use these pillars in this order: {pillars}.

Each post must feel distinct in hook style and tone: vary between emotional/parent-relatable, science/mechanism, and transformation/outcome formats.""" + B2C_HOOK_DIRECTIVE + """

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
""" + B2C_AUDIENCE_REALITY + """
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
""" + B2C_EXTRA_RULES + """
Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

FACEBOOK_USER_TEMPLATE = """Generate 5 Facebook posts for this week. Use these pillars in this order: {pillars}. Vary the length: include 2 short posts (80 to 130 words) and 3 medium posts (150 to 250 words). Each post must feel distinct in hook style and tone: vary between emotional/parent-relatable, science/mechanism, and transformation/outcome formats.""" + B2C_HOOK_DIRECTIVE + """

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
# LinkedIn carries an "audiences" block, so the runner uses the multi-audience
# path for evergreen runs. Instagram and Facebook have no audiences block, so
# they run the original single-call path unchanged.
PLATFORMS = {
    "linkedin": {
        "label": "LinkedIn",
        "network": "linkedin",
        "account_id": "68360d90c7a351d4c0097a84",
        "model": MODEL_SONNET,
        "system_prompt": LINKEDIN_SYSTEM,
        "user_template": LINKEDIN_USER_TEMPLATE,
        "audiences": LINKEDIN_AUDIENCES,
        "audience_weights": LINKEDIN_AUDIENCE_WEIGHTS,
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


# ---------------------------------------------------------------------------
# Campaign overlays (on-demand, fired from the Actions tab or --campaign)
# ---------------------------------------------------------------------------
# A campaign temporarily overrides a platform's pillar sequence and appends a
# focus addendum to its system prompt. Campaign runs bypass the audience split
# and do NOT advance the evergreen rotation.
CAMPAIGNS = {
    "centene": {
        "label": "Centene payor sequence",
        "platform": "linkedin",
        "pillars": [
            "Payor ROI",
            "Clinical Outcomes",
            "Neurodiversity Awareness",
            "BrainyAct Product",
            "Thought Leadership",
        ],
        "system_addendum": """

CAMPAIGN FOCUS (payor sequence):
This run targets decision-makers at a large Medicaid managed care organization. Tune every post to payor economics and managed-care priorities. Do NOT name Centene or any specific payor in the post text; the audience should recognize their own priorities without being named.

Frame posts around:
- Total cost of care and avoidable utilization, including emergency department diversion and crisis reduction
- HEDIS and quality-measure alignment, and behavioral health access gaps
- Value-based and at-risk contracting, and how a scalable digital intervention lowers per-member cost
- Member and family access at population scale, especially in underserved and rural Medicaid populations
- The downstream cost of underdiagnosis and delayed intervention

Keep clinical credibility high and the tone built for a payor evaluating a vendor. Every post still ends with a CTA referencing brainyact.com.""",
    },
}
