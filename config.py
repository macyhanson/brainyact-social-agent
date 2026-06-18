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
- Always end with the exact CTA assigned to the post
- Never name competitors
- No em dashes
- No generic AI opener phrases like "In today's landscape"
- Mix clinical credibility with conversational voice
- Hashtags: follow the per-post hashtag instruction exactly
- BrainyAct is positioned as a complement to ABA therapy, not a replacement
- Refer to the company only as "Kinuu" or the product as "BrainyAct by Kinuu". Never write "Kinuu Inc." or "Kinuu, LLC".

Claims integrity (strict):
- Default to qualitative outcomes. Obey each post's numericPolicy exactly.
- Never cite the 473-user dataset, participant counts, or internal numeric outcome statistics as effectiveness evidence. Do not invent numbers. Any external statistic must be a well-established, directional public fact.
- Avoid "proven", "rewire", "cure", and "treatment" used as a medical efficacy claim.

Respond ONLY with a valid JSON array. No preamble, no markdown fences, no explanation."""

# Template kept for the campaign path (single-audience, count-aware, now batched).
LINKEDIN_USER_TEMPLATE = """Generate {count} LinkedIn posts. Use these pillars in this order: {pillars}. Vary the length: include {short_n} short posts (150 to 250 words) and {medium_n} medium posts (300 to 500 words). Each post must feel distinct in structure and tone from the others. Include #BrainyAct #Neurodiversity #DigitalTherapeutics plus 2 pillar-specific tags in each post.

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
# run both stay balanced. To add an audience: add it here and define its profile
# below. Care coordinators are parked for now (omitted here), so they are not
# generated; add "careCoordinators" back to re-enable.
LINKEDIN_AUDIENCE_WEIGHTS = {"payors": 16, "employers": 14}

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
        "who": "Payor clinical and strategy leaders: Chief Medical Officers, Chief Behavioral Health Officers, Medicaid plan presidents, VPs of clinical strategy and population health, directors of pediatric care management, autism services, behavioral health, and complex case management, plus value-based care, innovation, quality, utilization management, and health equity leaders. Secondary: managed care consultants, state Medicaid stakeholders, and autism benefit managers.",
        "pains": "Access gaps and waitlists, downstream cost from delayed support, high-intensity service reliance, fragmented care pathways, limited functional outcomes visibility, weak home carryover, care management burden, member experience tied to caregiver burden, and pressure to move toward value-based developmental and behavioral health care.",
        "value_props": "A scalable adjunctive developmental support layer that meets neurodivergent members and families earlier: structured programming, caregiver involvement, home implementation, and functional progress visibility that complements existing services rather than replacing them.",
        "language": "Direct, strategic, payor-aware. Sounds like a clinical strategy leader, behavioral health operator, value-based care strategist, or care management executive. Short paragraphs, confident statements, no hype. Speak to cost, access, outcomes, care management, and value-based care.",
        "pillars": [
            "Access Gaps Drive Downstream Cost",
            "Outcomes Visibility in Developmental Care",
            "Caregiver Burden as Clinical Risk",
            "Upstream Alternatives Before Escalation",
            "Home Implementation Is the Missing Link",
            "Better Tools for Care Management",
            "Value-Based Care Needs Functional Outcomes",
        ],
        "cta": "This belongs in the payor strategy conversation.",
        "cta_bank": [
            "This is the gap BrainyAct is working to close.",
            "This belongs in the payor strategy conversation.",
            "This is where developmental care, behavioral health, and care management need to move next.",
            "Payors evaluating autism, ADHD, pediatric behavioral health, or caregiver support should be looking here.",
            "If your plan is focused on access, outcomes, and upstream support, this is worth discussing.",
            "The next step is not more volume. It is better support, earlier.",
        ],
        "cta_strong": [
            "BrainyAct is looking to partner with payors interested in measurable developmental support for neurodivergent members and families.",
            "We are open to conversations with Medicaid and commercial plans exploring scalable family-centered support models.",
            "If your team is rethinking autism, ADHD, pediatric behavioral health, or caregiver support, BrainyAct should be part of the conversation.",
        ],
        "hashtags": False,
        "word_short": "130 to 180",
        "word_medium": "190 to 250",
        "numeric_policy": _QUALITATIVE + " Use claim-safe framing only (designed to support, may help, complements, helps create visibility into). No cost-savings or claims-reduction figures unless validated by payor-specific data.",
        "system_addendum": "\n\nWrite for a payor clinical or strategy leader. Every post should connect to at least one payor priority: avoidable cost, access, earlier support, measurable outcomes, reduced service intensity, care-manager support, network gaps, member experience, value-based care, or caregiver burden before crisis. Mention BrainyAct lightly as a complementary, upstream, measurable, home-supported developmental layer, never a replacement. Do not attack existing services, overuse 'broken system', or imply payors do not care. No hashtags. No emojis.",
        "formats": [
            {"name": "Hook, problem, payor implication, BrainyAct, soft CTA", "guide": "Open on a sharp hook, state the family-level problem, make the payor implication explicit (cost, access, complexity, care management), connect BrainyAct lightly, close with a soft CTA."},
            {"name": "Contrarian statement", "guide": "Open with a bold contrarian line (a waitlist is not a care pathway), explain why it holds for payors, then say what the plan should do."},
            {"name": "What claims data does not show", "guide": "Contrast what a claim or utilization figure tells you with what it does not (function, regulation, family stability), then name the outcomes-visibility gap."},
            {"name": "Care-manager reality", "guide": "Show the limited options a care manager has (directory, referral, waitlist), then argue for an actionable, structured support families can use now."},
            {"name": "Reframe", "guide": "Reframe a familiar idea for payors, e.g. the caregiver is part of the care model, or upstream support is prevention by another name."},
        ],
        "hook_bank": [
            "A waitlist is not a care pathway.",
            "Access is not the same as support.",
            "Utilization is not the same as progress.",
            "A claim tells you what was billed. It does not tell you what changed.",
            "Caregiver burden is a care management issue.",
            "A provider directory is not a solution for every family.",
            "The home is where the care plan is tested.",
            "The next phase of autism care needs better outcomes visibility.",
            "Payors cannot manage developmental care with claims data alone.",
            "Families need more than authorization. They need implementation.",
            "The most expensive support is often the support that starts too late.",
            "Developmental care needs an upstream layer.",
            "Care managers need more than referral options.",
            "If the caregiver is overwhelmed, the care plan is already at risk.",
            "Value-based care requires more than service volume.",
            "Pediatric behavioral health needs scalable support models.",
            "The question is not only whether care was delivered. It is whether function improved.",
        ],
        "topics": [
            "Why waitlists are a payor problem",
            "Why access alone is not enough",
            "Why autism services need better outcomes visibility",
            "Why claims data does not show functional progress",
            "Why caregiver burden belongs in care management strategy",
            "Why provider directories are not enough",
            "Why payors need upstream developmental support",
            "Why care managers need actionable family support tools",
            "Why home implementation matters",
            "Why pediatric behavioral health needs scalable models",
            "Why value-based care needs functional outcomes",
            "Why developmental care should not be measured only in hours",
            "Why high-intensity service reliance creates cost pressure",
            "Why families need support before crisis",
            "Why Medicaid plans need practical family-centered solutions",
            "Why member experience depends on caregiver experience",
            "Why fragmented care pathways fail families",
            "Why payors should support the family system, not just the diagnosis",
        ],
        "training": {
            "examples": [
                """A waitlist is not a care pathway.

For families raising children with autism, ADHD, sensory processing challenges, or developmental delays, waiting does not mean needs are paused. It means parents are improvising. Schools are calling. Behaviors are escalating. Caregivers are burning out. Care managers are left with limited options.

That matters for payors. Because access gaps do not stay isolated. They can become higher complexity, higher family stress, lower engagement, and more expensive downstream needs.

BrainyAct was built as a scalable developmental support layer for neurodivergent members and families. Structured programming, caregiver involvement, home implementation, measurable progress. Not as a replacement for existing services, but as a way to give families a practical next step when the system has too few of them.

This belongs in the payor strategy conversation.""",
                """A claim tells you a service happened.

It does not tell you whether a child became more regulated. Whether transitions got easier. Whether the parent felt more capable. Whether school calls decreased. Whether the family is functioning better at home.

That is one of the biggest gaps in developmental and behavioral health care. Payors are often asked to fund services without enough visibility into functional progress.

Hours matter. Access matters. Provider quality matters. But outcomes have to matter too.

BrainyAct is built around structured developmental support and progress tracking, so families and stakeholders can see what is changing over time.

The future of autism, ADHD, and pediatric behavioral health support cannot be measured only by utilization. It has to be measured by function.""",
                """Caregiver burden is not outside the care model. It is part of the care model.

For a child with autism, ADHD, sensory processing challenges, or developmental delays, progress depends on the environment around the child. The routines. The regulation strategies. The caregiver's capacity. The consistency between sessions.

When the caregiver is overwhelmed, the care plan is already at risk.

That is why payors need to look at family-centered developmental support differently. The parent is often the person trying to implement everything after the appointment ends.

BrainyAct was designed with caregiver involvement and home implementation built in. Because supporting the member often means supporting the family system around them.

That is not soft. That is clinical strategy.""",
                """Care managers cannot solve every access problem with a referral.

Sometimes the provider network is full. Sometimes the family is on three waitlists. Sometimes the child needs support now, but the next appointment is months away. Sometimes the parent needs practical guidance, not another phone number.

This is where developmental and behavioral health care needs more flexible support models. Payors need solutions that give care management teams something actionable to offer families. Something structured. Something measurable. Something that supports the home and complements existing services without adding fragmentation.

BrainyAct was built for this gap. A scalable developmental support model for neurodivergent members and families who need more than a directory.

Care management works better when families have a real next step.""",
            ],
            "facts": [
                "Internal pre/post data does not meet payor evidence standards; a controlled efficacy trial is in progress. Speak to outcomes qualitatively.",
                "Strongest payor lane: payors need better upstream, measurable, family-centered support for neurodivergent members, and BrainyAct fills that gap.",
                "Position BrainyAct as a scalable adjunctive, upstream, caregiver-enabled, home-supported developmental program. Never a replacement for ABA or therapy, a cure, a low-cost shortcut, a generic app, a wellness tool, a game, or a utilization-management tactic.",
            ],
            "requires": [
                "Connect to at least one payor priority (cost, access, earlier support, measurable outcomes, service intensity, care management, network gaps, member experience, value-based care, or caregiver burden)",
                "Direct, strategic, payor-aware voice with short paragraphs and confident statements",
                "Mention BrainyAct lightly as a complementary upstream measurable home-supported developmental layer",
                "Use claim-safe language: designed to support, may help, complements, helps create visibility into",
            ],
            "bans": [
                "Hashtags",
                "Emojis",
                "Hype, motivational-speaker, or parent-influencer tone",
                "Sounding like a SaaS ad or a pitch deck turned into a post",
                "Attacking existing services, overusing 'broken system', or implying payors do not care",
                "'DM me' style closers",
                "Overclaims: reduces claims, prevents autism, cures, replaces ABA/OT/speech/behavioral health, guarantees outcomes, eliminates need for higher care, or saves payors a dollar figure",
                "Participant counts or internal outcome numbers",
            ],
        },
    },
    # PARKED: not in LINKEDIN_AUDIENCE_WEIGHTS, so it is not generated.
    # Re-add "careCoordinators" to the weights to bring this audience back.
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
        "who": "Benefits decision-makers at large self-insured employers: CHROs, VP of Total Rewards, VP and Director of Benefits, health and welfare leaders, well-being and employee experience leaders, DEI and neurodiversity leaders, workforce mental health and leave/absence leaders, and the benefits consultants, TPAs, and stop-loss advisors who serve them.",
        "pains": "Health benefit cost growth, pediatric behavioral health access gaps, long waitlists, caregiver burden and lost productivity, dependent-care complexity, undifferentiated family benefits, overreliance on high-cost high-hour models, and a lack of measurable outcomes in child-focused benefits.",
        "value_props": "A scalable, measurable, caregiver-centered developmental benefit that supports neurodivergent families before crisis: a bridge between waitlists, therapy, and home implementation, with outcome visibility employers can actually use.",
        "language": "Executive-level and direct. Short sentences, one idea per post, strong hook, clear point of view. Employer-relevant language: caregiver burden, absenteeism, presenteeism, productivity, retention, utilization versus impact, upstream cost, dependent care. Insightful, slightly provocative, empathetic, strategic. Not fluffy, not clinical-heavy, not an ad.",
        "pillars": [
            "Caregiver Burden as Workforce Issue",
            "Waitlists Are Not a Neutral Delay",
            "Measurable Family Benefits",
            "Neurodiversity Includes Caregivers",
            "Home Engagement Is the Missing Link",
            "Upstream Cost Pressure",
        ],
        "cta": "This belongs in the benefits strategy conversation.",
        "cta_bank": [
            "This is a conversation more self-insured employers should be having.",
            "This is the gap BrainyAct is working to close.",
            "Benefits leaders building family support strategies should be looking here.",
            "Worth discussing if your 2026 benefits strategy includes neurodiversity, behavioral health, or caregiver support.",
            "If your organization is rethinking dependent-care benefits, this belongs in the conversation.",
            "This is where family benefits need to evolve.",
            "Large self-insured employers should be looking here.",
        ],
        "cta_strong": [
            "We are looking to partner with large self-insured employers that want to offer more measurable support for neurodivergent families.",
            "If your benefits team is evaluating family mental health, autism, ADHD, or caregiver support solutions, BrainyAct should be on the list.",
            "I would welcome conversations with benefits leaders exploring more scalable developmental support for employees' families.",
        ],
        "hashtags": False,
        "word_short": "120 to 160",
        "word_medium": "170 to 220",
        "numeric_policy": "No BrainyAct outcome numbers or participant counts, and no medical claims. You MAY reference the public employer cost-trend figures listed in the facts, with their source. Do not invent other statistics.",
        "system_addendum": "\n\nWrite for a benefits decision-maker at a large self-insured employer. Sound like a sharp practitioner, not an ad. The throughline across posts is the hidden workforce cost of unsupported neurodivergent families: employers already pay for it through productivity loss, caregiver burnout, behavioral health claims, navigation burden, and retention risk. Mention BrainyAct lightly, usually near the end, as a complementary, upstream, home-supported developmental benefit. No hashtags. No emojis.",
        "formats": [
            {"name": "Problem, reframe, implication", "guide": "State the problem benefits leaders see, reframe it, make the workforce implication explicit, tie BrainyAct in lightly near the end, close with a soft CTA."},
            {"name": "Contrarian statement", "guide": "Open with a bold contrarian line, explain why it holds, then say what employers should do about it."},
            {"name": "What benefits leaders are missing", "guide": "Name the metric they track (utilization), contrast it with what they miss (family relief, easier mornings, fewer school calls), name the next frontier."},
            {"name": "Family reality vignette", "guide": "Open on a concrete home moment (a 7 a.m. meltdown, a school call between meetings), then connect it to absenteeism, presenteeism, productivity, and retention."},
            {"name": "Data-anchored strategy", "guide": "Anchor on a public employer cost-trend figure from the facts (with source), then argue for measurable upstream family support."},
        ],
        "hook_bank": [
            "Waitlists are not a neutral delay.",
            "Caregiver burden is a workforce issue.",
            "The next frontier in neurodiversity benefits is not only the employee. It is the employee's family.",
            "A provider directory is not a family support strategy.",
            "Utilization is not the same as impact.",
            "The home is the setting most benefits forget.",
            "Some of your most capable employees are quietly drowning in care coordination.",
            "An EAP referral is not enough for every family.",
            "The employee may be at work, but their stress started at home.",
            "Large employers are missing a major dependent-care gap.",
            "Family-friendly benefits often miss the families with the most complex needs.",
            "If your neurodiversity strategy stops at hiring, it is incomplete.",
            "The most expensive support is often the support that starts too late.",
            "Benefits leaders need to stop confusing access with outcomes.",
        ],
        "topics": [
            "The hidden workforce cost of parenting a neurodivergent child",
            "Why waitlists are a benefits problem",
            "Why autism benefits need to evolve beyond claims access",
            "Why caregiver burden belongs in workforce mental health strategy",
            "How self-insured employers can support families before crisis",
            "Why utilization is not enough to measure benefit value",
            "Why home-supported intervention matters",
            "Why employees need more than an EAP referral",
            "Why neurodiversity strategy must include caregivers",
            "Why high-cost services need upstream complements",
            "Why pediatric behavioral health is an employee productivity issue",
            "Why family-friendly benefits often miss complex families",
            "Why measurable developmental support belongs in benefit design",
            "Why access alone is not the same as outcomes",
        ],
        "training": {
            "examples": [
                """The employee sitting in your 9 a.m. meeting may have already handled more before work than most people handle all day.

A meltdown before school. A call from the teacher. A therapy schedule that does not fit into a workday. A child on a waitlist with no clear next step.

This is the reality for many employees raising neurodivergent children.

Caregiver burden is not separate from workforce strategy. It affects focus, attendance, productivity, retention, and emotional capacity.

Large self-insured employers have spent years expanding mental health benefits, but many still miss one of the biggest sources of employee stress: what is happening inside the family system.

BrainyAct was built for this gap. Structured developmental support, caregiver involvement, home implementation, measurable progress.

Because supporting the employee means supporting the family they are carrying with them into work every day.

This belongs in the benefits strategy conversation.""",
                """A waitlist is not a pause button.

For families raising children with autism, ADHD, sensory processing challenges, or developmental delays, a six-month waitlist is six months of daily problem-solving without enough support.

Six months of school calls. Six months of dysregulated mornings. Six months of stress that follows them into work.

Employers often think about waitlists as a healthcare access issue. They are also a workforce issue.

When support is delayed, the burden does not disappear. It shifts to the caregiver. That caregiver is often your employee.

Large self-insured employers need family benefits that can support families while they are waiting, not only after they finally reach the front of the line.

The question for employers is simple: what support are you offering families before they reach crisis?""",
                """A benefit can have high utilization and still leave the core problem untouched.

Utilization tells you someone used the benefit. It does not tell you whether the family stabilized. Whether the caregiver felt less overwhelmed. Whether daily routines improved. Whether the child gained regulation, participation, or confidence.

For large self-insured employers, the next generation of benefits cannot only be measured by enrollment and clicks. They need outcome visibility, especially in pediatric behavioral health, autism support, and caregiver support.

BrainyAct was built around structured programming and measurable progress, not just access.

Because employers do not need more benefits that look good in a portal. They need benefits that show what changed.""",
                """An EAP referral is not enough for a parent whose child is melting down every morning before school.

A mental health app is not enough when the issue is developmental, sensory, behavioral, and family-wide. A provider directory is not enough when every clinic has a waitlist.

This is where many benefits strategies fall short. They offer resources. But families need implementation. They need structure. They need something that reaches the home.

For employees raising neurodivergent children, the stress is not abstract. It is daily, practical, and immediate.

BrainyAct was built for this level of support. Not as another generic wellness tool, but as a structured developmental benefit for families who need more than a link, a list, or a referral.""",
            ],
            "facts": [
                "Mercer reported average health benefit cost per employee rose 6.0 percent in 2025 and projected 6.7 percent for 2026, the highest increase in 15 years.",
                "Business Group on Health reported employers expect 2026 health care cost trend at a median of 9.0 percent before plan design changes and 7.6 percent after.",
                "LinkedIn B2B research: nearly three in four decision-makers consider thought leadership more trustworthy than product marketing. Posts should read as insight, not ads.",
                "Strongest content lane: the hidden workforce cost of unsupported neurodivergent families.",
                "Position BrainyAct as a scalable, measurable, home-supported developmental benefit. Never an app, wellness perk, therapy game, ABA replacement, cheaper autism benefit, or cure.",
            ],
            "requires": [
                "Executive-level, direct voice with short lines and one idea per post",
                "Make the employer implication explicit: productivity, absenteeism, presenteeism, retention, or cost",
                "Mention BrainyAct lightly, usually near the end, as a complementary upstream home-supported developmental benefit",
            ],
            "bans": [
                "Hashtags",
                "Emojis",
                "Hype words: revolutionary, game-changer, cutting-edge, unlock potential, transformative",
                "'We are excited to announce'",
                "Hard-sell closers like 'DM me to learn more'",
                "Medical claims, or cures, treats, prevents, guarantees outcomes",
                "Attacking or directly comparing against ABA",
                "Heavy clinical jargon",
                "Calling BrainyAct an app, wellness perk, therapy game, or cure",
            ],
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
