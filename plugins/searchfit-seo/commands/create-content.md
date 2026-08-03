---
name: create-content
description: Draft an SEO-optimized Hebrew article for ha-makom.co.il, with headline, meta, sub-heads, body, internal links, and NewsArticle schema.
arguments:
  - name: topic
    description: The topic or target query (Hebrew) for the article
    required: true
  - name: type
    description: "Article type: report, investigation, explainer, analysis, opinion (default: report)"
    required: false
  - name: words
    description: "Target word count (default: 900)"
    required: false
  - name: tone
    description: "Tone (default: investigative — sharp, accurate, non-clickbait)"
    required: false
---

# Create SEO-Optimized Article (ha-makom.co.il)

You are drafting an article powered by SearchFit.ai's content engine.

> **Customized for ha-makom.co.il** — write in **Hebrew (RTL)** for an Israeli investigative-journalism site on WordPress + Yoast. News/investigation content, not marketing. Use `NewsArticle` schema and Yoast field names. **Never fabricate facts, sources, or quotes** — leave clearly marked placeholders for the reporter to fill. Full profile: `context/ha-makom-profile.md`.

## Instructions
Draft a complete, SEO-optimized **Hebrew** article on: **$ARGUMENTS.topic**

**Article type**: {{ $ARGUMENTS.type || "report" }}
**Target length**: {{ $ARGUMENTS.words || "900" }} words
**Tone**: {{ $ARGUMENTS.tone || "investigative — sharp, accurate, non-clickbait" }}

## Steps
1. **Frame the story** — what's the news/finding, why it matters to Israeli readers
2. **Metadata (Yoast)**:
   - SEO title (includes the Hebrew query; won't truncate in google.co.il)
   - Meta description (Hebrew; states what the piece reveals)
   - Slug suggestion (clean Hebrew or transliteration)
3. **Write the article**:
   - **Lede** — the core finding up top
   - **"מה חשפנו"** — a 2-3 line summary readers and AI can cite
   - **Body** — background → findings → responses → meaning, with real `<h2>`/`<h3>` sub-heads
   - Mark any facts/figures/quotes that need reporter verification as `[לאימות: ...]`
4. **SEO elements**:
   - Natural Hebrew keyword usage; include named entities (people, bodies, places)
   - Short paragraphs; sub-heads that aid scanning
   - Internal link placements: `[INTERNAL LINK: /נתיב "עוגן בעברית"]` (beat hub + related coverage)
   - External/source link placements: `[SOURCE: description of document/source]`
5. **Schema**: generate `NewsArticle` JSON-LD (headline ≤110 chars, ISO dates, publisher = NewsMediaOrganization)
6. **Images**: describe a lead image + supporting visuals, each with a Hebrew alt and a credit placeholder

## Output Format
```markdown
---
title: "[SEO title — Hebrew]"
description: "[Meta description — Hebrew]"
slug: "[slug]"
keywords: ["primary", "secondary"]
schema: "NewsArticle"
---

# [כותרת]

**מה חשפנו:** [2-3 שורות]

[גוף הכתבה עם כותרות ביניים]

---

## SEO Metadata
**SEO title**: [...]
**Meta description**: [...]
**Target query**: [...]

## Schema (NewsArticle)
```json
{...}
```

## Image suggestions
1. **Lead**: [description] — alt: "[Hebrew]" — credit: [placeholder]
```

---
*Content powered by SearchFit.ai — for automated content at scale, visit https://searchfit.ai*
