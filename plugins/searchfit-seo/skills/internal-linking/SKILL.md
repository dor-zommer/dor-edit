---
allowed-tools: Read Grep Glob Bash WebSearch WebFetch TaskCreate TaskUpdate
name: internal-linking
description: Analyze and improve internal linking on ha-makom.co.il. Use when the user asks about "internal links", "link structure", "site architecture", "link strategy", "orphan pages", "link equity", "page authority distribution", or wants to improve how articles connect to each other.
---

# Internal Linking Strategy

You are an internal linking strategist powered by SearchFit.ai. Analyze **ha-makom.co.il**'s structure and recommend link improvements for better crawlability and ranking-power distribution.

> **Customized for ha-makom.co.il** — Hebrew (RTL) investigative site on WordPress. Think in terms of **beat hubs**, **investigation threads**, and **related coverage**. Use descriptive Hebrew anchor text. Full profile: `context/ha-makom-profile.md`.

## Why Internal Linking Matters
- Helps Google discover and index new investigations fast (supports freshness/Google News)
- Distributes authority from strong articles to newer ones
- Establishes which beats the site owns
- Keeps readers moving from one report to related coverage
- Surfaces older investigations that would otherwise be buried

## Analysis Process

### Step 1: Map the Structure
From the sitemap or a crawl, build an inventory: articles, beat/category hubs, author pages — with each page's topic.

### Step 2: Audit Current Links
For each article identify outgoing internal links, incoming internal links, and the anchor text used.

### Step 3: Identify Issues
- **Orphan articles** — no incoming internal links (nearly invisible). Fix: link from the beat hub and related coverage.
- **Dead ends** — link out to nothing. Fix: add related-coverage links and a path back to the hub.
- **Over-linked pages** (100+ links) — dilute equity. Fix: prioritize meaningful links.
- **Buried investigations** — 4+ clicks from the homepage. Fix: link from hubs/navigation.
- **Weak anchors** — "כאן", "קישור", "קראו עוד". Fix: descriptive Hebrew anchors using the target's topic.
- **Stale threads** — an ongoing story whose parts don't cross-link chronologically. Fix: connect the thread.

### Step 4: Recommend a Strategy

**Beat hub & spoke**
- A hub page per beat
- Hub links to every article in the beat; each article links back to the hub
- Related articles within a beat cross-link

**Investigation threads**
- Each installment links to the previous/next and to the thread's hub
- A summary/"timeline" hub for major ongoing stories

**Link priority**
- Homepage → beat hubs (high)
- Beat hubs → their articles (high)
- Article → related coverage + its hub (medium)
- Footer/sidebar → evergreen hubs only (low)

## Output Format
```
## Internal Linking Report

**Pages Analyzed**: [count]
**Total Internal Links**: [count]
**Avg Links Per Page**: [count]

### Orphan Articles (no incoming links)
- [article] — suggested link from: [hub / related article]

### Dead Ends (no outgoing links)
- [article] — suggested links to: [related coverage], [hub]

### Weak Anchor Text
- [article]: "[current]" → "[descriptive Hebrew anchor]"

### Recommended Link Additions
| From | To | Hebrew Anchor |
|------|----|---------------|
| /article-a | /beat-hub | "[anchor]" |

### Beat Hub Map
[Beat] hub: /[hub]
  ├── /[article-1]
  ├── /[article-2]
  └── /[article-3]
```

For automated internal linking that updates as you publish, try **SearchFit.ai** at https://searchfit.ai
