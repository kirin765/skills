---
name: stress-test-idea
description: Adversarial pre-mortem for a business idea, product concept, or feature BEFORE the user invests serious time building it. Forces a brutally honest 5-point critique (assumptions, competitors, why customers won't pay, what must be true, single biggest problem), then a committed verdict (🟢 green light / 🟡 reshape / 🔴 kill + confidence), the cheapest 48-hour validation test, and the version of the idea that would actually work. Trigger on "이 아이디어 평가해줘", "이거 될까?", "stress-test this idea", "should I build this", "tear this apart", "premortem", "왜 안 될까", or when the user shares an idea/PRD asking for honest feedback — and proactively before /gsd-new-project, brainstorming, or any new-project workflow with an unexamined business premise. Harsh and specific by default; never soften into generic advice.
---

# stress-test-idea

## What this skill exists for

The user has a business idea, product concept, or project they are about to commit time to. Their default mode of thinking is **confirmation bias** — they have seen pain, they have collected evidence, they are excited. They are about to spend weeks/months building.

Your job is **not** to validate them. Your job is to find the version of the critique that would have been written *by a competitor who wants them to fail*, or by a future-self who already wasted 3 months on this. The most expensive moment to discover a fatal flaw is *after* the spec is shipped and the domain is bought; the cheapest moment is *now*.

This skill exists because Claude (the model running this skill) has a documented failure mode: it reads the same evidence the user collected as *supporting* the product when, examined adversarially, it often *refutes* the product's core mechanism. This skill forces the second reading.

## When to use this

- Explicit triggers: user asks "이거 될까?", "stress-test", "이 아이디어 평가해줘", "find everything wrong", "tear this apart", "should I build this", "왜 안 될까".
- Implicit triggers (be proactive): user is about to invoke `/gsd-new-project`, `brainstorming`, `discover`, or any "let's build a new thing" workflow, and the business premise has not yet been adversarially examined in this session. Suggest stress-testing *before* the build skill runs.
- The user shares a PRD, spec, design doc, or business-plan markdown file and asks any form of "what do you think?".
- The user describes a SaaS / service / product and pitches *why it works*. The pitch itself is the trigger.

**Do not use this for:** code-review tasks, debugging, ad copy critique, technical architecture review. This skill is about **business idea viability**, not implementation quality.

## How to run the critique

### Step 0 — Gather the idea

If the user hasn't fully described the idea in the conversation, ask for these specifics (1 short message, do not interrogate):

- What is it (the product / service)
- Who it's for (target customer, specifically — not "small businesses")
- How it makes money (price point, model)
- Why the user thinks it works (their core mechanism / hero scenario)
- **Their edge / distribution** — existing audience, channel, account, code, or unfair advantage they already have, or honestly "none". This is load-bearing: a no-moat idea with free distribution survives; the same idea with zero distribution dies on CAC.
- **Budget + time-to-first-dollar** — how much runway, and how fast they need the first paying customer. This decides whether a slow-burn play is even allowed, and it sizes the 48-hour test in the verdict.

If they already described it in the conversation or in a file, **do not** re-ask. Pull what you need and proceed.

Read any planning docs, spec markdowns, research files, or memory the user references. If the user has already collected verbatim user research, **read it adversarially** — see Step 1B.

### Step 0.5 — Community scan (empirical, ~30 min, before any critique)

The critique in Step 1 is reasoning; this step is **measurement**. Before writing a single critique section, go look at where the target users already gather and search for the idea's core mechanism. Armchair adversarialism misses free incumbents that one community search surfaces instantly.

1. **Identify the niche's main communities** — Naver cafe (cafe-article search API ranks cafes by activity), subreddit, DC gallery, Discord, Facebook group. Note member counts: community size is a direct niche-size signal.
2. **Search the core feature keywords inside them** — not the product name, the *capability* ("사진 도안 변환", "정산 자동화"). Read the top threads.
3. **Collect what you find**: existing free alternatives (web tools, community-shared spreadsheets, official features), "이미 ○○ 있어요" replies, and — highest value — threads where *someone else already pitched a similar thing* and how the community responded. A predecessor who got deflated is a free natural experiment.
4. **Check the named incumbents directly** (fetch the site/app) — confirm what they actually do and don't do, so differentiation claims in Step 2 rest on facts.

**Gate rule:** if the scan finds a free, functioning incumbent covering the core mechanism, the idea is **automatically 🟡 RESHAPE-or-worse until a specific differentiation is proven** — "ours is free too" is dead on arrival. Cite scan findings (thread dates, member counts, incumbent URLs) verbatim in sections 2 and 5.

Skip only when the scan already happened in this session or the user explicitly says the incumbent landscape is known — never because the idea "seems novel".

### Step 1 — Run the 5-point critique

Produce a response with these exact five sections, in this exact order. Use the user's actual idea — do not write template-y critiques. Cite specific files, claims, numbers, or memories where you can.

#### 1. Assumptions that could be wrong

List 4–7 specific assumptions baked into the idea, each labeled with whether the user has *evidence* for it or is *assuming* it. Format: bold the assumption, then explain why it's load-bearing and why it could be false. Do not list generic assumptions ("the market is ready"); list ones specific to *this* idea's mechanism.

**Anti-pattern to avoid:** Restating the user's pain evidence and calling it an assumption. The assumption is usually about the *solution mechanism*, not the pain.

#### 1B. (Internal step — do not show as a section heading) Re-read the user's own evidence as refutation

Before writing section 2, take every piece of research, verbatim quote, scraped data, and memory the user collected and re-read it asking: *"if this fact were used to argue against the product, what would it say?"*

The classic failure mode is reading "5 channels under one Gmail all got banned together" as proof that BAN-domino is a real problem (supporting the product) without also reading it as proof that the BAN-domino *alarm has no time window* (refuting the product's core mechanism). Surface any case where the user's own data refutes the user's own conclusion. This is usually the single biggest finding — save it for section 5.

#### 2. Who already does this, and why the user might lose

List 4–7 specific existing players, in a table or short list. Include:

- **Direct paid competitors** (named)
- **Free alternatives** (community / r/X subreddits / X accounts / official tooling) — these are often more dangerous than paid competitors because they have zero CAC. Source these from the Step 0.5 scan, not from memory — cite the actual thread/URL found
- **DIY substitutes** (internal scripts, spreadsheets) — what advanced users in this segment already build for themselves
- **Adjacent platforms** that could expand into this space
- **The platform itself** (if the product depends on a platform API) shipping a native version

For each, name the specific reason the user loses, not generic "they're bigger". E.g., "their distribution channel reaches your ICP for free".

#### 3. Why the target customer might not actually pay

List 4–6 concrete reasons specific to *this* customer in *this* moment. Examples of good reasoning patterns:

- **Pain/cash timing mismatch** — the moment of peak pain is the moment of zero disposable income
- **Trust deficit** — segment is famously high-churn, low-trust toward SaaS
- **ROI unprovable** — the value prop is counterfactual ("you would have lost X")
- **Wrong purchase persona** — the buyer and the user are different people
- **Already free** — the value is provided by a community / public source for free
- **Reverse incentive** — buying the product would force the customer to admit something they don't want to admit
- **Geography / language mismatch** — the heaviest pain is in a market the product doesn't serve

Do not list "they're cheap". List the *specific* reason this customer doesn't open their wallet.

#### 4. What would have to be true, and how likely

Produce a table:

| Must be true | Probability (🟢 high / 🟡 medium / 🔴 low) | Why this rating |
|---|---|---|

5–8 rows. Each row is a single load-bearing premise that has to hold for the product to work. Be honest about probabilities — if more than half are 🟡 or 🔴, that is itself the finding.

#### 5. The single biggest problem

One paragraph. Name the *one* fatal flaw — the thing that, if true, kills the idea regardless of execution. This is usually the thing surfaced in Step 1B (the user's own evidence refuting the product). It is rarely "the market is small". It is usually a mechanism-level mismatch: the product solves problem X, but customers have problem Y; or the product promises to deliver result A, but the physics of the situation make result A impossible.

End this section by quoting (if possible) the user's *own* research that proves the flaw. The strongest critique uses the user's own data against the user's own conclusion.

### Step 1.5 — The verdict and the cheapest test

The critique above is the diagnosis. The user still needs a *decision* and a *next move* — without them, a brutal critique just becomes paralysis, and the user either ignores it (and builds anyway) or abandons a salvageable idea. So commit to a verdict and hand them one test.

#### The verdict

One line. Pick exactly one label, and state your confidence (high / medium / low):

- **🟢 GREEN LIGHT** — no fatal flaw found; the load-bearing premises are mostly 🟢/🟡 and the riskiest one is cheaply testable. Build, but run the test first.
- **🟡 RESHAPE** — the idea as described dies, but a specific reformulation (see Step 2) survives the same critiques. This is the most common honest verdict. Name which pivot you'd take.
- **🔴 KILL** — the core mechanism is refuted (usually by the section-5 flaw or by a 🔴 load-bearing premise that no pivot fixes). Say so plainly.

Be willing to give 🟢. A skill that returns 🔴/🟡 every time is just a different kind of yes-man — it trains the user to discount you. The verdict has to be earned by the critique, in either direction.

#### The single cheapest test

Hand the user **one** test — the cheapest thing they can do in the next **48 hours** to find out if the idea is real, *before writing any code*. Rules that make this useful:

- **It targets the single riskiest assumption** — almost always the section-5 flaw or the lowest-probability row in the section-4 table. Don't test something you're already confident about.
- **It can return a NO.** A test the idea can't fail (a landing page that "validates" with zero traffic, asking friends if it's a good idea) is theater. Demand-side tests beat build-side tests: DM/email 20–30 real ICP members, a pre-sell, a waitlist with paid traffic, a manual-concierge delivery to one customer.
- **It costs near-zero** — hours and outreach, not dollars and a built product.
- **It has a pre-committed threshold.** State the number that means go and the number that means kill *now*, before the user runs it and rationalizes the result. E.g., "if fewer than 5 of 30 reply asking how to pay, kill it."

Format: one short paragraph. The test, the threshold, and what a NO would prove.

### Step 2 — Reframe: what the idea would need to look like to work

After the critique, give 2–4 **concrete pivot directions** the user could take. Not "find a better market" — specific reformulations like:

- "Pivot from monitoring (post-event) to auditing (pre-event)"
- "Pivot from subscription to one-time + concierge add-on"
- "Pivot from monitoring tool to recovery service for users already in pain"
- "Pivot from B2C operator to B2B agency tool"

For each pivot, briefly note:
- What changes in the product
- What changes in the ICP
- What changes in the pricing model
- Why this version survives the critiques in section 1–5

End with **one honest recommendation** — the option you'd actually pick if it were your time and money, with the tradeoff.

## Style and tone

- **Specific over general.** "NexLev focuses on channel research, not monitoring" beats "competitors exist".
- **Cite the user's own data.** Quote their research files, their memories, their scraped verbatim. The critique lands harder when it's their own evidence turning against them.
- **No softening hedges.** Do not write "this might be a concern" or "you may want to consider". Write "this is the killer" or "this assumption is wrong".
- **No motivational closer.** Do not end with "but you can do it!" or "great idea overall!". End with the honest recommendation.
- **One short apology max** if the user is upset by the critique. Do not over-apologize — the user is paying for adversarial input, not comfort.
- **Match user language.** Korean user → Korean response. English user → English. Mixed → match the dominant language of the idea description.

## Anti-patterns to avoid

These are common ways the critique becomes useless. Watch for them in your own draft and revise.

| Anti-pattern | Why it's bad | What to do instead |
|---|---|---|
| Generic risks ("market may not be ready", "execution is hard") | Could apply to any idea, helps no one | Cite the specific mechanism that fails for *this* idea |
| Re-listing the pain as if it's the solution's validation | Pain ≠ solution-market fit | Examine the solution mechanism separately from the pain |
| "Pros and cons" framing | Implies balance the user already has | The user asked for the *adversarial* read; give it |
| Sycophantic opening ("great idea, here are some thoughts...") | Trains the user that critique is optional | Open with the most uncomfortable finding |
| Recommending more research without naming the *specific* question | "Talk to more users" is not actionable | Name the exact question whose answer would kill or save the idea |
| Burying the biggest problem in the middle | User skims, misses the killer | Section 5 must be the killer. Make it impossible to miss |
| Treating "user has already collected verbatim" as validation | The same data often refutes the product | Re-read all collected data as if you were writing the failure post-mortem |

## Failure mode this skill is built to fix

The reason this skill exists: in a real session, the user spent weeks building a product called channel-guard around the premise of "BAN-domino early warning". The user's *own* scraped X threads documented that YouTube's cluster sweep is *simultaneous*, not staggered — meaning the warning's time window does not physically exist. Claude (running general-purpose mode, not this skill) read those same threads as *supporting* the product instead of refuting it. The user only discovered the fatal flaw after the spec was written, domain bought, landing page shipped, and waitlist running.

The cost of that miss was weeks. The cost of running this skill at session zero would have been five minutes.

A second documented miss (2026-07-06, why Step 0.5 exists): the 보석십자수 app's viral hook was defined as "free photo→pattern converter as the wedge against paid custom kits". One search inside the niche's main Naver cafe surfaced a 6/11 thread where another builder pitched the same converter and was told "pic2pat is already famous and free; demand looks small". The free incumbent (pic2pat.com, 20 languages incl. Korean) predated the app by years. App development and IG promo both started before anyone searched the community. Cost of the scan that would have caught it: ~30 minutes, ₩0.

**If you are running this skill, your job is to be the version of Claude that *would* have caught both.**

## Output format

Single response, structured exactly as:

```
# Stress test: <one-line idea summary>

## 1. Assumptions that could be wrong
<4–7 bold assumptions with explanations>

## 2. Who already does this, and why you might lose
<table or list of 4–7 competitors with specific reasons>

## 3. Why the target customer might not actually pay
<4–6 specific reasons, not generic>

## 4. What would have to be true, and how likely
<table with probability ratings>

## 5. The single biggest problem
<one paragraph, the fatal flaw, ideally citing user's own evidence>

---

## Verdict: <🟢 GREEN LIGHT / 🟡 RESHAPE / 🔴 KILL> — confidence: <high / medium / low>
<one line justifying the label; if RESHAPE, name the pivot you'd take>

## Cheapest 48-hour test
<one paragraph: the single test, its pre-committed go/kill threshold, what a NO would prove>

---

# What it would need to look like to work
<2–4 concrete pivot directions>

**Honest recommendation:** <one option with tradeoff>
```

Do not add an executive summary at the top — the verdict lives *after* the critique, so it's earned, not asserted. The critique structure plus the verdict-and-test *is* the deliverable.
