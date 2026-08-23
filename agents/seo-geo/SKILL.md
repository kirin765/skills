---
name: seo-geo
description: >
  Optimize content for AI Overviews (formerly SGE), ChatGPT web search,
  Perplexity, and other AI-powered search experiences. Generative Engine
  Optimization (GEO) analysis including brand mention signals, AI crawler
  accessibility, llms.txt compliance, passage-level citability scoring, and
  platform-specific optimization. Use when user says "AI Overviews", "SGE",
  "GEO", "AI search", "LLM optimization", "Perplexity", "AI citations",
  "ChatGPT search", or "AI visibility".
user-invokable: true
argument-hint: "[url]"
license: MIT
metadata:
  author: AgriciDaniel
  version: "1.10.0"
  category: seo
---

# AI Search / GEO Optimization (February 2026)

## Key Statistics

| Metric | Value | Source |
|--------|-------|--------|
| AI Overviews reach | 1.5 billion users/month across 200+ countries | Google |
| AI Overviews query coverage | 50%+ of all queries | Industry data |
| AI-referred sessions growth | 527% (Jan-May 2025) | SparkToro |
| ChatGPT weekly active users | 900 million | OpenAI |
| Perplexity monthly queries | 500+ million | Perplexity |

## Critical Insight: Brand Mentions > Backlinks

**Brand mentions correlate 3x more strongly with AI visibility than backlinks.**
(Ahrefs December 2025 study of 75,000 brands)

| Signal | Correlation with AI Citations |
|--------|------------------------------|
| YouTube mentions | ~0.737 (strongest) |
| Reddit mentions | High |
| Wikipedia presence | High |
| LinkedIn presence | Moderate |
| Domain Rating (backlinks) | ~0.266 (weak) |

**Only 11% of domains** are cited by both ChatGPT and Google AI Overviews for the same query, so platform-specific optimization is essential.

---

## How ChatGPT Actually Fetches & Cites (mechanism, high-confidence)

From a network-traffic teardown of ChatGPT's own internal labels (Suganthan Mohanadasan, Jun 2026 — reading the decrypted JSON the engine sends the browser, not a black-box prompt study). These are **structural facts** (a field exists / how it behaves); treat any percentage as directional.

**One-line model:** ChatGPT reads **your page for the facts** (if it can parse them) and **everyone else's page for the opinion** — and only when the query is worth a search. It is *not* a blue-link search engine.

### Four gates that decide visibility

1. **Does it even search? (`turn_use_case`)** — every query is bucketed before any fetch. The `text` bucket = **answered from training, ZERO web fetch** (how-tos, definitions, code, even some current high-stakes questions). Wording, not topic, picks the bucket. → *Confirm the target query triggers a fetch before optimizing a page for it; training-answered queries can't be won by any page.*
2. **Who fetched it? (`result_source`)** — every fetched result is stamped `serp` (open-web baseline), `labrador` (**licensed publisher tier** — Reuters/WSJ/Wikipedia/arXiv, near-full-article snippets, effectively closed), `bright` (**Bright Data scraper — bulk of fetching**), or `oxylabs` (rival scraper, regional/local). → *You compete in the scraped `bright`/`oxylabs` tier — be cleanly scrapable: facts in plain HTML text, never JS/PDF/image.*
3. **Fetched ≠ Cited ≠ Mentioned** — three independent outcomes. **Cited** binds to a *specific sentence* (topical relevance isn't enough — be the best support for an exact claim). Results **dedupe by domain** → 20 thin pages collapse to 1; **one strong page per claim beats a pile of weak ones** (do NOT mass-produce a thin page per fan-out query). **Text gets cited, video doesn't** — a YouTube fetch returns metadata, not transcript, so nothing binds (Reddit cited heavily, YouTube ~never; Ahrefs 1.93% vs 0.51%).
4. **The JavaScript trap** — the thinking model goes to the *official page first* for facts (pricing/specs), but when pricing is **behind JavaScript** its saved reasoning says *"pricing isn't showing… possibly loaded with JavaScript,"* gives up, and **cites G2 / a third party instead.** A JS pricing table doesn't just rank badly — **it hands your numbers to a competitor's profile.**

### Fan-out (thinking model)
One question → ~15–40 sub-queries. It fires `site:vendor.com/pricing` probes, **guesses a price then searches to confirm**, widens to tools you never named, and greps the page for `$`/`€`/numbers. → *Survive a `site:yourdomain.com/pricing` probe; avoid JS toggles / dynamic data loading; put numbers in crawlable text.*

### Can't be optimized
- **Personalization** — answers can pull the user's own `convo_search`/`gmail`/`files`; two users get different answers, visibility scores wobble.
- **Local cap** — `local_results_limit: 2`; for "near me" you're top-2 or invisible.
- **No client-visible ranking score** — domain authority / trust weights stay server-side; "ChatGPT ranking factors" products are snake-oil.

### What this changes about the advice below
- **Own your facts in plain HTML** (pricing/specs as crawlable text) is now a *#1, mechanism-proven* lever, not a nice-to-have.
- **You can't cite yourself** — earn the recommendation off-site (reviews, Reddit, honest comparison content); that's where the verdict gets cited from.
- **One strong page per claim**, not thin pages per query (domain dedupe).
- **Prefer fetch-triggering queries** (comparison, "with reviews", shopping, local, pricing) over training-answered how-tos/definitions.

### Self-audit recipe (run on any target)
DevTools → Network → Preserve log → run the query → Cmd+Opt+F search `result_source` to see the pipeline per link. Console (`allow pasting`) → fetch `/backend-api/conversation/<id>` with the `/api/auth/session` token and walk the JSON for `result_source` to pull fetch/citation/reasoning. Reads only the user's own session.

---

## GEO Analysis Criteria (Updated)

### 1. Citability Score (25%)

**Optimal passage length: 134-167 words** for AI citation.

**Strong signals:**
- Clear, quotable sentences with specific facts/statistics
- Self-contained answer blocks (can be extracted without context)
- Direct answer in first 40-60 words of section
- Claims attributed with specific sources
- Definitions following "X is..." or "X refers to..." patterns
- Unique data points not found elsewhere

**Weak signals:**
- Vague, general statements
- Opinion without evidence
- Buried conclusions
- No specific data points

### 2. Structural Readability (20%)

**92% of AI Overview citations come from top-10 ranking pages**, but 47% come from pages ranking below position 5, demonstrating different selection logic.

**Strong signals:**
- Clean H1->H2->H3 heading hierarchy
- Question-based headings (matches query patterns)
- Short paragraphs (2-4 sentences)
- Tables for comparative data
- Ordered/unordered lists for step-by-step or multi-item content
- FAQ sections with clear Q&A format

**Weak signals:**
- Wall of text with no structure
- Inconsistent heading hierarchy
- No lists or tables
- Information buried in paragraphs

### 3. Multi-Modal Content (15%)

Content with multi-modal elements sees **156% higher selection rates**.

**Check for:**
- Text + relevant images
- Video content (embedded or linked)
- Infographics and charts
- Interactive elements (calculators, tools)
- Structured data supporting media

### 4. Authority & Brand Signals (20%)

**Strong signals:**
- Author byline with credentials
- Publication date and last-updated date
- Citations to primary sources (studies, official docs, data)
- Organization credentials and affiliations
- Expert quotes with attribution
- Entity presence in Wikipedia, Wikidata
- Mentions on Reddit, YouTube, LinkedIn

**Weak signals:**
- Anonymous authorship
- No dates
- No sources cited
- No brand presence across platforms

### 5. Technical Accessibility (20%)

**AI crawlers do NOT execute JavaScript.** Server-side rendering is critical.

**Check for:**
- Server-side rendering (SSR) vs client-only content
- AI crawler access in robots.txt
- llms.txt file presence and configuration
- RSL 1.0 licensing terms

---

## AI Crawler Detection

Check `robots.txt` for these AI crawlers:

| Crawler | Owner | Purpose |
|---------|-------|---------|
| GPTBot | OpenAI | ChatGPT web search |
| OAI-SearchBot | OpenAI | OpenAI search features |
| ChatGPT-User | OpenAI | ChatGPT browsing |
| ClaudeBot | Anthropic | Claude web features |
| PerplexityBot | Perplexity | Perplexity AI search |
| CCBot | Common Crawl | Training data (often blocked) |
| anthropic-ai | Anthropic | Claude training |
| Bytespider | ByteDance | TikTok/Douyin AI |
| cohere-ai | Cohere | Cohere models |

**Recommendation:** Allow GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot for AI search visibility. Block CCBot and training crawlers if desired.

---

## llms.txt Standard

The emerging **llms.txt** standard provides AI crawlers with structured content guidance.

**Location:** `/llms.txt` (root of domain)

**Format:**
```
# Title of site
> Brief description

## Main sections
- [Page title](url): Description
- [Another page](url): Description

## Optional: Key facts
- Fact 1
- Fact 2
```

**Check for:**
- Presence of `/llms.txt`
- Structured content guidance
- Key page highlights
- Contact/authority information

---

## RSL 1.0 (Really Simple Licensing)

New standard (December 2025) for machine-readable AI licensing terms.

**Backed by:** Reddit, Yahoo, Medium, Quora, Cloudflare, Akamai, Creative Commons

**Check for:** RSL implementation and appropriate licensing terms.

---

## Platform-Specific Optimization

| Platform | Key Citation Sources | Optimization Focus |
|----------|---------------------|-------------------|
| **Google AI Overviews** | Top-10 ranking pages (92%) | Traditional SEO + passage optimization |
| **ChatGPT** | Wikipedia (47.9%), Reddit (11.3%) | Entity presence, authoritative sources |
| **Perplexity** | Reddit (46.7%), Wikipedia | Community validation, discussions |
| **Bing Copilot** | Bing index, authoritative sites | Bing SEO, IndexNow |

---

## Output

Generate `GEO-ANALYSIS.md` with:

1. **GEO Readiness Score: XX/100**
2. **Platform breakdown** (Google AIO, ChatGPT, Perplexity scores)
3. **AI Crawler Access Status** (which crawlers allowed/blocked)
4. **llms.txt Status** (present, missing, recommendations)
5. **Brand Mention Analysis** (presence on Wikipedia, Reddit, YouTube, LinkedIn)
6. **Passage-Level Citability** (optimal 134-167 word blocks identified)
7. **Server-Side Rendering Check** (JavaScript dependency analysis)
8. **Top 5 Highest-Impact Changes**
9. **Schema Recommendations** (for AI discoverability)
10. **Content Reformatting Suggestions** (specific passages to rewrite)

---

## Quick Wins

1. Add "What is [topic]?" definition in first 60 words
2. Create 134-167 word self-contained answer blocks
3. Add question-based H2/H3 headings
4. Include specific statistics with sources
5. Add publication/update dates
6. Implement Person schema for authors
7. Allow key AI crawlers in robots.txt

## Medium Effort

1. Create `/llms.txt` file
2. Add author bio with credentials + Wikipedia/LinkedIn links
3. Ensure server-side rendering for key content
4. Build entity presence on Reddit, YouTube
5. Add comparison tables with data
6. Implement FAQ sections (structured, not schema for commercial sites)

## High Impact

1. Create original research/surveys (unique citability)
2. Build Wikipedia presence for brand/key people
3. Establish YouTube channel with content mentions
4. Implement comprehensive entity linking (sameAs across platforms)
5. Develop unique tools or calculators

## DataForSEO Integration (Optional)

If DataForSEO MCP tools are available, use `ai_optimization_chat_gpt_scraper` to check what ChatGPT web search returns for target queries (real GEO visibility check) and `ai_opt_llm_ment_search` with `ai_opt_llm_ment_top_domains` for LLM mention tracking across AI platforms.

## Error Handling

| Scenario | Action |
|----------|--------|
| URL unreachable (DNS failure, connection refused) | Report the error clearly. Do not guess site content. Suggest the user verify the URL and try again. |
| AI crawlers blocked by robots.txt | Report exactly which crawlers are blocked and which are allowed. Provide specific robots.txt directives to add for enabling AI search visibility. |
| No llms.txt found | Note the absence and provide a ready-to-use llms.txt template based on the site's content structure. |
| No structured data detected | Report the gap and provide specific schema recommendations (Article, Organization, Person) for improving AI discoverability. |
