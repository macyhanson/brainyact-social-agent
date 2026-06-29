// BrainyAct LinkedIn B2B — scheduled runner (Path B)
// Generates 5 payor + 5 employer single posts and 2 employer carousels,
// pushes the 10 single posts to Publer as drafts, writes carousel scripts to
// out/, and appends to ledger.json so angles never repeat across runs.
//
// Requires Node 20+ (global fetch). Env vars (set as GitHub secrets):
//   ANTHROPIC_API_KEY, PUBLER_API_KEY, PUBLER_WORKSPACE_ID, PUBLER_LINKEDIN_ACCOUNT_ID
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";

const MODEL = "claude-sonnet-4-20250514";
const LEDGER_PATH = new URL("./ledger.json", import.meta.url);
const LEDGER_CAP = 80;
const SINGLE_MIX = { payors: 5, employers: 5 };
const CAROUSEL_MIX = { employers: 2 };
const BATCH_SIZE = 5;

const {
  ANTHROPIC_API_KEY,
  PUBLER_API_KEY,
  PUBLER_WORKSPACE_ID = "680fe03e02cf6a3063e9468e",
  PUBLER_LINKEDIN_ACCOUNT_ID = "68360d90c7a351d4c0097a84",
} = process.env;

if (!ANTHROPIC_API_KEY) { console.error("Missing ANTHROPIC_API_KEY"); process.exit(1); }
if (!PUBLER_API_KEY) { console.error("Missing PUBLER_API_KEY"); process.exit(1); }

// ---------- Content config (kept in sync with SKILL.md) ----------
const SITE_FACTS = `BrainyAct by Kinuu. Tagline: "Putting Hope in Motion." Brand line: "Transformation, not just treatment."
Reimagined developmental care, visible results in 6 months, zero wait time, personalized programs. Ages 6+, with or without a formal diagnosis.
Conditions: autism spectrum, ADHD, sensory processing disorder, dyslexia, dyscalculia, dysgraphia, adoption trauma, anxiety.
Bottom-up developmental model grounded in functional neurology. Complement to ABA, not a replacement.
Pages: brainyact.com/the-science, brainyact.com/for-businesses. Expert call: meetings.hubspot.com/macy-hanson/macy.`;

const APPROVED_STATS = `Use ONLY these external stats, and ALWAYS attribute them. Never present any of these as a BrainyAct outcome:
- About 1 in 31 children are identified with autism by age 8 (CDC ADDM, 2025 report, 2022 data).
- About 1 in 6 children (roughly 17%) aged 3 to 17 has one or more developmental disabilities (CDC National Health Interview Survey, Zablotsky et al.). Use for the broad neurodevelopmental-prevalence hook; keep the "developmental disabilities" wording and CDC attribution.
- 54% of employers now cover ABA therapy (Gallagher 2025 Benefits Benchmarks).
- High-cost autism claims above $200K grew roughly 78% year over year, 2023 to 2024 (Mercer).
- Active ABA at recommended intensity (10 to 40 hrs/week, $120 to $200/hr) runs about $50,000 to $100,000+ per child per year; broad-population average is about $20,000/year (2017 data).
- 43% of autism caregivers reduce hours or leave the workforce (Gnanasekaran et al., 2015).
- 46% of parents of a child with ADHD reduced work hours after diagnosis; 11% stopped working.
- Caregiver-related productivity loss is estimated at over $25 billion a year across the US workforce (directional).`;

const PRODUCT_FACTS = `Approved product facts (descriptive, allowed for all audiences): 275 data points tracked per child across six domains (Motor, Sensory, Behavior, Communication, Academic, Health); fixed 4 to 6 month duration; home-based and gamified; ages 6+; bottom-up developmental sequencing.`;

const COST_MODEL = `The ONE approved cost model (employers only): traditional behavioral health is about $130,000 per member, roughly $13M per 100 members over three years. BrainyAct is under $20,000 per member, under $2M per 100, with outcomes in six months. Potential savings exceed $13M. This is BrainyAct's own cost comparison, not third-party data. Do not use any other cost or savings figure.`;

const AUDIENCES = {
  payors: {
    label: "Insurance Payors / Health Plans",
    who: "Medical directors, utilization and care management leaders, behavioral health policy owners at health plans and Medicaid MCOs.",
    pains: "Prolonged high-intensity service spend, crisis-driven encounters, restrictive placements, limited utilization visibility, pressure on total cost of care and HEDIS measures.",
    valueProps: "Fewer crisis-driven encounters, less reliance on restrictive environments, improved daily functioning, data visibility for utilization planning, reduced reliance on prolonged high-intensity services.",
    language: "Total cost of care, utilization, member outcomes, medical policy, ED diversion, HEDIS, evidence threshold. Measured, credible, non-hyped.",
    pillarsPreferred: ["Payor ROI", "Thought Leadership", "Clinical Outcomes", "Neurodiversity Awareness"],
    cta: "Read the payor brief at brainyact.com/for-businesses, or book a call at meetings.hubspot.com/macy-hanson/macy.",
    numericPolicy: "QUALITATIVE ONLY. No percentages, no participant counts, no cost figures, no stats of any kind.",
  },
  employers: {
    label: "Self-Insured Employers",
    who: "Benefits leaders, total rewards, HR directors, VP Benefits, and CFOs at self-insured employers carrying dependent neurodevelopmental care.",
    pains: "Open-ended behavioral health claims with no discharge criteria or outcome data, rising high-cost autism claims, caregiver absenteeism and presenteeism, benefits that do not differentiate, no proof of ROI, full ERISA claims exposure.",
    valueProps: "A fixed 4 to 6 month program with a real finish line, machine-readable outcome data across six domains, whole-child multi-condition care in one program, caregiver relief that stabilizes work performance, ERISA flexibility to act now.",
    language: "Open-ended claims, off-ramp, discharge criteria, outcome data, total cost, caregiver productivity, ERISA flexibility, benefits differentiation. Business-first, plain, CFO-ready.",
    pillarsPreferred: ["Employer Benefits", "Payor ROI", "Neurodiversity Awareness", "Thought Leadership"],
    cta: "See the employer overview at brainyact.com/for-businesses, or book a 20-minute ROI walkthrough at meetings.hubspot.com/macy-hanson/macy.",
    numericPolicy: "Approved external stats (always attributed), approved product facts, and the one approved cost model are allowed. NO internal outcome figures. NO guarantee language. You may critique the ABA reimbursement model (open-ended, unmeasured, no discharge), never ABA clinically.",
  },
};

const TRAINING = {
  payors: {
    examples: [
      "Most digital health tools ask neurodiverse kids to adapt to the platform. BrainyAct works the other way around. Built by Kinuu for individuals ages 6 to 30 with autism, ADHD, dyslexia, and related conditions, it builds functional skills through structured, engaging experiences that feel less like therapy and more like something a child actually wants to return to. For payors and benefits decision-makers, the operational profile matters as much as the clinical one. BrainyAct is home-based and scalable, so it reaches members in rural and underserved communities without a clinic visit. It complements existing ABA and behavioral health services rather than creating a parallel track. And it is built for sustained engagement, because a digital intervention members abandon after two sessions does not move quality metrics or reduce utilization. Real-world progress. Skill development that extends beyond the session. See what BrainyAct looks like inside a managed care strategy at brainyact.com. #BrainyAct #Neurodiversity #DigitalTherapeutics #ValueBasedCare #BehavioralHealthTech",
      "Most digital tools for neurodivergent individuals were built to track behavior. BrainyAct was built to change it. A lot of tools in this space generate data. Far fewer generate progress. BrainyAct by Kinuu is a patent-pending gamification-based neurolearning platform for individuals ages 6 to 30. The engagement is built into the architecture, not layered on top, because it is grounded in how neurodivergent brains respond to reward, repetition, and mastery. It is designed to function alongside ABA therapy, not compete with it. And it tracks functional behavior, cognitive skill acquisition, and caregiver-reported quality of life qualitatively, so progress is visible rather than assumed. For payors and clinical programs adding a scalable, evidence-informed digital layer to neurodevelopmental care, BrainyAct is worth a serious look. Explore the platform at brainyact.com. #BrainyAct #Neurodiversity #DigitalTherapeutics #BehavioralHealth #ValueBasedCare",
    ],
    requires: ["Credible, measured tone", "Frame around total cost of care and member outcomes", "Open on a two-part antithesis (what other tools do, then flip to BrainyAct) or a sharp reframe; this drove the strongest engagement", "Use staccato fragment triads for emphasis", "Before the CTA, ask one measured, answerable question to invite replies (comments drive reach; recent posts earned none)", "Close on a soft, low-friction CTA"],
    bans: ["Any number or percentage", "'proven', 'rewire', 'cure'", "Competitor names", "Internal participant counts (e.g. the 473-user dataset)"],
  },
  employers: {
    examples: [
      "We spent $15M treating 100 kids with autism and ADHD. Know how many improved enough to reduce services? We don't. Because nobody tracked it. That's the self-insured employer's quiet problem with behavioral health benefits. Every other medical benefit has outcome benchmarks. Why not behavioral health? BrainyAct runs a fixed 4 to 6 month program and tracks 275 data points per child across six domains, so the plan can finally see what it paid for. If this math matters to your plan, happy to show you. #employeebenefits #selffunded #behavioralhealth",
      "Hot take: open-ended ABA authorizations are one of the most expensive line items in a self-funded plan, and most TPAs have no off-ramp for them. No discharge criteria. No outcome data. No end date. You would never accept that from a surgical vendor. It is not a family problem, it is a protocol problem. There is another path: a fixed-duration program with measured results across six developmental domains and a clear point where a child graduates. Happy to walk through it. No deck. 20 minutes. #selfinsured #employeebenefits #behavioralhealth",
      "Neurodiversity is not a problem to solve. It is a population to serve better. About 1 in 6 children in the US has a developmental disability such as autism, ADHD, or a learning disability (CDC, National Health Interview Survey). The clinical system, for all its strengths, was not built to serve this population at scale. Waitlists are long. Access is uneven. Consistent, engaging, skill-targeted intervention produces results; the challenge has always been consistency and access. That is what BrainyAct was built to address, not to replace clinicians but to extend the reach of their work into the hours and spaces where most of life actually happens. For employers and health plans serving neurodiverse populations, the conversation starts with access. Learn more at brainyact.com. #BrainyAct #Neurodiversity #DigitalTherapeutics #WorkforceInclusion #HealthEquity",
    ],
    requires: ["Business-first, CFO-ready framing", "One idea per line; this audience skims", "Soft CTAs", "Attribute every external stat", "Open on a two-part antithesis or clean reframe; these drove the strongest engagement", "Use staccato fragment triads for emphasis", "Before the soft CTA, ask one genuine question benefits leaders would answer (comments drive reach; recent posts earned none)"],
    bans: ["Internal outcome percentages (incl. 91%)", "Any guarantee language", "The $150K/$43M cost version", "Hashtag stuffing (max 5)", "Attacking ABA clinically", "Internal participant counts (e.g. the 473-user dataset)"],
  },
};

const FORMATS = [
  { name: "Contrarian take", guide: "Name a belief the audience holds, then flip it and defend the flip." },
  { name: "Mini case story", guide: "One short anonymized narrative of a single family or organizational situation. No names." },
  { name: "Numbered framework", guide: "Tight numbered list (3-4 items)." },
  { name: "Question-led", guide: "Open with a sharp question the audience is actually asking, answer it across the post." },
  { name: "Reframe", guide: "Reframe a familiar concept." },
  { name: "First-person clinical POV", guide: "Expert thinking out loud using OT and functional-neurology framing." },
  { name: "Myth-bust", guide: "Name a specific misconception, dismantle it with reasoning." },
  { name: "Direct provocation", guide: "Short, punchy challenge to the status quo, then a crisp reason it matters." },
  { name: "Trend read", guide: "Take a current access/coverage trend and draw a practical implication." },
  { name: "Cost-model anchor", guide: "EMPLOYERS ONLY. Open on the approved cost model and draw the plan-level implication. CFO-ready. No other numbers." },
];

const HOOKS = ["The validated winner: a concrete product-contrast antithesis. What most tools do TO the neurodiverse user, then flip to what BrainyAct does FOR them ('Most tools ask kids to adapt to the platform. BrainyAct works the other way around'). In June 2026 data every engaged post used this flip; abstract aphorisms and long essays drew reach but zero engagement. Lead with it.", "A bold one-line claim", "A surprising but well-established external fact", "A specific question", "A short scene or moment", "A misconception stated flatly, then flipped", "A list promise", "A blunt cost-or-time observation"];

const CAROUSEL_STRATEGIES = [
  { name: "Provocative Stat", slides: 7, arc: "Cover = pattern-interrupt stat/question. Then: name the problem, deepen the pain, introduce the standard every other benefit meets, the BrainyAct difference, the ROI punchline (approved cost model), soft CTA." },
  { name: "Contrarian Take", slides: 6, arc: "Cover = contrarian opener about the ABA reimbursement model. Then: the specifics, flip the frame (protocol not family problem), the family side, the alternative (fixed duration, six domains, finish line), soft CTA. Critique payment structure, never ABA clinically." },
  { name: "CFO Direct Address", slides: 6, arc: "Cover = direct address to self-insured plans. Then: the problem in three crisp lines, remove the blame, the alternative exists, the number (approved cost model on its own slide), shortest CTA." },
];

const SYSTEM_PROMPT = `You are a B2B LinkedIn content strategist for BrainyAct by Kinuu, a patent-pending gamification-based neurolearning platform for ages 6+ with autism, ADHD, dyslexia, and related neurodevelopmental conditions.

Grounding facts (use these, do not contradict them):
${SITE_FACTS}

${PRODUCT_FACTS}

Brand rules:
- End with the assigned CTA. Where it fits the audience, precede the CTA with ONE genuine, answerable question to the reader to invite replies. Comments and reshares are the primary driver of LinkedIn reach; recent posts earned zero of either, so a reply-worthy question is the highest-leverage addition.
- Favor concrete over abstract, and keep posts tight. In recent data the longest, most abstract essay-style post drew reach but zero engagement, while sharp concrete posts converted.
- Never name competitors or specific people at named firms. No em dashes. No generic AI openers.
- Mix clinical credibility with conversational voice. Use 3 to 5 hashtags, leading with #BrainyAct #Neurodiversity #DigitalTherapeutics. One idea per line for skimmers.
- BrainyAct is a complement to ABA, not a replacement. Refer to the company only as "Kinuu" or the product as "BrainyAct by Kinuu". Never write "Kinuu Inc." or "Kinuu, LLC".

Claims integrity (STRICT, obey each item's numericPolicy exactly):
- Payors: fully qualitative. No numbers at all.
- Employers: you MAY use the approved external stats (always attributed), approved product facts, and the single approved cost model below. Nothing else numeric.
${APPROVED_STATS}
${COST_MODEL}
- BANNED for everyone: the 91% figure and any internal outcome percentage or participant count; the $150K/$43M cost version; any performance or outcome guarantee; "proven", "rewire", "cure", "treatment" as an efficacy claim.
- ABA: complement, not replacement. Employers may critique the ABA reimbursement model but never attack ABA clinically.

Variety mandate (most important):
- Each item has a distinct FORMAT/STRATEGY, HOOK, and angle. Follow them exactly. Never reuse an angle or opening line listed as already-used.

Respond ONLY with valid JSON. No preamble, no markdown fences.`;

// ---------- helpers ----------
function shuffle(arr) { const a = [...arr]; for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

function ledgerBlock(ledger) {
  if (!ledger.length) return "";
  const recent = ledger.slice(-LEDGER_CAP);
  return `\nALREADY USED (this run and prior runs) — do NOT repeat any of these angles or opening lines:\n${recent.map(l => `- [${l.audience}] ${l.opening} (${l.topic})`).join("\n")}`;
}

function buildBatchPrompt(audienceKeys, ledger) {
  const fmts = shuffle(FORMATS), hooks = shuffle(HOOKS);
  const lengths = shuffle(["short", "short", "medium", "medium", "medium"]);
  const blocks = audienceKeys.map((key, i) => {
    const a = AUDIENCES[key], t = TRAINING[key] || {};
    const pillar = shuffle(a.pillarsPreferred)[0];
    let fmt = fmts[i % fmts.length];
    if (fmt.name === "Cost-model anchor" && key !== "employers") fmt = FORMATS[0];
    const ex = (t.examples && t.examples.length) ? `\n  Imitate the voice of these proven posts (do not copy text):\n  ${t.examples.map(e => `"${e.slice(0, 500)}"`).join("\n  ")}` : "";
    return `Post ${i + 1}
  Audience: ${a.label}
  Who they are: ${a.who}
  Their pains: ${a.pains}
  Value props: ${a.valueProps}
  Voice/language: ${a.language}
  Pillar: ${pillar}
  Format: ${fmt.name} — ${fmt.guide}
  Hook style: ${hooks[i % hooks.length]}
  Length: ${lengths[i]} (${lengths[i] === "short" ? "150-250" : "300-500"} words)
  CTA: ${a.cta}
  numericPolicy: ${a.numericPolicy}
  Must include: ${(t.requires || []).join("; ") || "n/a"}
  Must avoid: ${(t.bans || []).join("; ") || "n/a"}${ex}`;
  }).join("\n\n");
  return `Generate exactly ${audienceKeys.length} LinkedIn single posts. Each must read as structurally different from every other item.

${blocks}
${ledgerBlock(ledger)}

Return a JSON array with one object per post:
{ "audience": "audience label", "pillar": "pillar", "format": "format name", "length": "short|medium", "topic": "5-8 word summary", "hook": "first line", "body": "full post text including hook, body, CTA, hashtags" }`;
}

function buildCarouselPrompt(audienceKey, strategy, ledger) {
  const a = AUDIENCES[audienceKey], t = TRAINING[audienceKey] || {};
  const pillar = shuffle(a.pillarsPreferred)[0];
  const ex = (t.examples && t.examples.length) ? `\nVoice anchors (imitate tone, do not copy):\n${t.examples.map(e => `"${e.slice(0, 400)}"`).join("\n")}` : "";
  return `Generate ONE LinkedIn carousel for this audience.

Audience: ${a.label}
Who they are: ${a.who}
Their pains: ${a.pains}
Value props: ${a.valueProps}
Voice/language: ${a.language}
Pillar: ${pillar}
Strategy: ${strategy.name} (${strategy.slides} slides)
Slide arc to follow: ${strategy.arc}
CTA direction: ${a.cta} (final slide is a soft version)
numericPolicy: ${a.numericPolicy}
Must include: ${(t.requires || []).join("; ") || "n/a"}
Must avoid: ${(t.bans || []).join("; ") || "n/a"}${ex}
${ledgerBlock(ledger)}

Each slide: 1-3 short lines of copy plus a one-line design note. Slide 1 is the cover/hook. The caption ends with the soft CTA and 3 to 5 hashtags.

Return ONE JSON object:
{ "audience": "${a.label}", "pillar": "${pillar}", "strategy": "${strategy.name}", "title": "short title", "topic": "5-8 word summary", "hook": "cover first line", "slides": [ { "n": 1, "copy": "slide copy", "design": "design note" } ], "caption": "LinkedIn caption with CTA and hashtags" }`;
}

async function callApi(userContent, maxTokens) {
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01" },
    body: JSON.stringify({ model: MODEL, max_tokens: maxTokens, temperature: 0.9, system: SYSTEM_PROMPT, messages: [{ role: "user", content: userContent }] }),
  });
  if (!res.ok) throw new Error(`Anthropic ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  const raw = data.content?.[0]?.text || "";
  return JSON.parse(raw.replace(/```json|```/g, "").trim());
}

async function pushToPubler(text) {
  const res = await fetch("https://app.publer.io/api/v1/posts/schedule", {
    method: "POST",
    headers: {
      "Authorization": `Bearer-API ${PUBLER_API_KEY}`,
      "Publer-Workspace-Id": PUBLER_WORKSPACE_ID,
      "Content-Type": "application/json",
      "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    },
    body: JSON.stringify({
      bulk: { state: "draft", posts: [{ networks: { linkedin: { type: "status", text } }, accounts: [{ id: PUBLER_LINKEDIN_ACCOUNT_ID }] }] },
    }),
  });
  const body = await res.text();
  if (!res.ok) throw new Error(`Publer ${res.status}: ${body.slice(0, 200)}`);
  return body;
}

// ---------- main ----------
async function main() {
  const ledger = existsSync(LEDGER_PATH) ? JSON.parse(await readFile(LEDGER_PATH, "utf8") || "[]") : [];
  const stamp = new Date().toISOString().slice(0, 10);

  // singles
  const singleQueue = shuffle(Object.entries(SINGLE_MIX).flatMap(([k, n]) => Array(n).fill(k)));
  const posts = [];
  for (let i = 0; i < singleQueue.length; i += BATCH_SIZE) {
    const batch = singleQueue.slice(i, i + BATCH_SIZE);
    let parsed;
    try { parsed = await callApi(buildBatchPrompt(batch, ledger), 8000); }
    catch { parsed = await callApi(buildBatchPrompt(batch, ledger), 8000); }
    if (!Array.isArray(parsed)) throw new Error("Batch did not return an array.");
    for (const p of parsed) {
      posts.push(p);
      ledger.push({ date: stamp, audience: p.audience || "", opening: (p.hook || p.body || "").slice(0, 80), topic: p.topic || "" });
    }
    console.log(`Generated single batch (${batch.length}), total ${posts.length}`);
  }

  // carousels
  const carouselQueue = shuffle(Object.entries(CAROUSEL_MIX).flatMap(([k, n]) => Array(n).fill(k)));
  const carousels = [];
  for (const key of carouselQueue) {
    const strategy = shuffle(CAROUSEL_STRATEGIES)[0];
    let car;
    try { car = await callApi(buildCarouselPrompt(key, strategy, ledger), 4000); }
    catch { car = await callApi(buildCarouselPrompt(key, strategy, ledger), 4000); }
    if (!car || !Array.isArray(car.slides)) throw new Error("Carousel did not return slides.");
    carousels.push(car);
    ledger.push({ date: stamp, audience: car.audience || "", opening: (car.hook || car.title || "").slice(0, 80), topic: car.topic || "" });
    console.log(`Generated carousel: ${car.title}`);
  }

  // push singles to Publer as drafts
  let ok = 0, fail = 0;
  for (const p of posts) {
    try { await pushToPubler(p.body); ok++; }
    catch (e) { fail++; console.error(`Publer push failed: ${e.message}`); }
  }
  console.log(`Publer drafts: ${ok} ok, ${fail} failed`);

  // write carousel scripts to out/
  await mkdir(new URL("./out/", import.meta.url), { recursive: true });
  const md = carousels.map(c => {
    const slides = c.slides.map(s => `SLIDE ${s.n}\n${s.copy}\n(design: ${s.design})`).join("\n\n");
    return `## ${c.strategy} — ${c.audience} — "${c.title}"\n\n${slides}\n\nCAPTION:\n${c.caption}\n`;
  }).join("\n---\n\n");
  await writeFile(new URL(`./out/carousels-${stamp}.md`, import.meta.url), `# Employer carousels — ${stamp}\n\n${md}`);
  console.log(`Wrote out/carousels-${stamp}.md`);

  // persist ledger (capped)
  await writeFile(LEDGER_PATH, JSON.stringify(ledger.slice(-LEDGER_CAP), null, 2));
  console.log(`Ledger now holds ${Math.min(ledger.length, LEDGER_CAP)} entries`);

  if (ok === 0 && posts.length > 0) process.exit(1); // nothing landed
}

main().catch(e => { console.error(e); process.exit(1); });
